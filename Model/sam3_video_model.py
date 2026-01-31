"""
SAM3 Video Model Wrapper for Pothole Detection
Uses SAM3 text prompts for initial detection + SAM3 Video Tracker for tracking
"""

import torch
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from pathlib import Path
import cv2
from PIL import Image


class SAM3VideoModel:
    """
    Video-based pothole detection using SAM3.
    
    Workflow:
    1. Load video and process it through SAM3 Video Tracker
    2. Use text prompts to detect potholes on first frame(s)
    3. Track detected potholes through entire video automatically
    4. No manual deduplication needed - model handles object identity
    """

    def __init__(self, model_id: str = "facebook/sam3", device: str = "cuda"):
        """
        Initialize SAM3 Video model.
        
        Args:
            model_id: Hugging Face model ID
            device: Preferred device ('cuda', 'mps', or 'cpu')
        """
        # Device selection
        if device == "cuda" and torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
            
        self.model_id = model_id
        self.video_model = None
        self.video_processor = None
        self.image_model = None
        self.image_processor = None
        
        print(f"Initializing SAM3 Video on device: {self.device}")

    def load_models(self) -> bool:
        """Load both SAM3 image model (for detection) and video model (for tracking)"""
        try:
            from transformers import (
                Sam3Model, Sam3Processor,
                Sam3TrackerVideoModel, Sam3TrackerVideoProcessor
            )
            
            print("Loading SAM3 models...")
            print("  This may take a while on first run (~3.4GB download)")
            
            # Load image model for text-prompted detection
            print("  Loading image model for text detection...")
            self.image_processor = Sam3Processor.from_pretrained(self.model_id)
            self.image_model = Sam3Model.from_pretrained(self.model_id).to(self.device)
            self.image_model.eval()
            
            # Load video model for tracking
            print("  Loading video model for tracking...")
            self.video_processor = Sam3TrackerVideoProcessor.from_pretrained(self.model_id)
            self.video_model = Sam3TrackerVideoModel.from_pretrained(self.model_id).to(
                self.device, dtype=torch.bfloat16
            )
            self.video_model.eval()
            
            print("✓ SAM3 models loaded successfully")
            print(f"  Device: {self.device}")
            return True
            
        except ImportError as e:
            print(f"✗ Error: SAM3 dependencies not installed")
            print(f"  {e}")
            print("\nTo install: pip install transformers>=4.47.0")
            return False
            
        except Exception as e:
            print(f"✗ Error loading SAM3 models: {e}")
            return False

    def detect_with_text(
        self,
        image: Union[np.ndarray, Image.Image],
        text_prompts: Union[str, List[str]],
        threshold: float = 0.5
    ) -> List[Dict]:
        """
        Detect objects using text prompts (SAM3's concept detection).
        
        Args:
            image: Input image (RGB numpy array or PIL Image)
            text_prompts: Text description(s) of what to detect
            threshold: Confidence threshold
            
        Returns:
            List of detections with masks, boxes, and scores
        """
        if self.image_model is None:
            raise RuntimeError("Models not loaded. Call load_models() first.")
            
        # Convert to PIL if needed
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
            
        if isinstance(text_prompts, str):
            text_prompts = [text_prompts]
            
        # Process with text prompt
        text_for_processor = text_prompts[0] if text_prompts else "object"
        
        inputs = self.image_processor(
            images=image,
            text=text_for_processor,
            return_tensors="pt"
        )
        
        target_sizes_raw = inputs.pop("original_sizes", None)
        inputs = {k: v.to(self.device) if hasattr(v, 'to') else v for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.image_model(**inputs)
            
        # Post-process
        target_sizes = target_sizes_raw
        if target_sizes is not None and hasattr(target_sizes, "tolist"):
            target_sizes = target_sizes.tolist()
        if not target_sizes:
            target_sizes = [[image.height, image.width]]
            
        results = self.image_processor.post_process_instance_segmentation(
            outputs,
            threshold=threshold,
            mask_threshold=0.5,
            target_sizes=target_sizes
        )[0]
        
        # Convert to our format
        detections = []
        scores = results.get("scores", results.get("score", []))
        masks = results.get("masks", [])
        boxes = results.get("boxes", [])
        
        if not hasattr(scores, "__len__"):
            scores = [scores]
        if not hasattr(masks, "__len__"):
            masks = [masks]
        if not hasattr(boxes, "__len__"):
            boxes = [boxes]
            
        for i in range(len(scores)):
            sc = scores[i].item() if hasattr(scores[i], "item") else float(scores[i])
            if sc >= threshold:
                mask = masks[i].cpu().numpy() if hasattr(masks[i], "cpu") else np.array(masks[i])
                box = boxes[i].cpu().numpy() if hasattr(boxes[i], "cpu") else np.array(boxes[i])
                
                if box.size >= 4:
                    x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                else:
                    x1, y1, x2, y2 = 0, 0, 0, 0
                    
                # Get centroid for tracking
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                    
                detections.append({
                    'mask': mask,
                    'bbox': [x1, y1, x2 - x1, y2 - y1],  # [x, y, w, h]
                    'box_xyxy': [x1, y1, x2, y2],
                    'centroid': [cx, cy],
                    'area': float(np.sum(mask > 0.5)),
                    'confidence': sc,
                    'label': text_prompts[0] if text_prompts else "object"
                })
                
        return detections

    def process_video(
        self,
        video_path: str,
        text_prompts: List[str] = ["pothole", "road damage"],
        detection_threshold: float = 0.5,
        detection_frame_interval: int = 30,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        Process entire video for pothole detection using video tracking.
        
        Args:
            video_path: Path to video file
            text_prompts: Text prompts for initial detection
            detection_threshold: Confidence threshold for detection
            detection_frame_interval: Run text detection every N frames to find new objects
            output_dir: Directory to save results
            
        Returns:
            Dictionary with tracked objects and their trajectories
        """
        if self.video_model is None:
            raise RuntimeError("Models not loaded. Call load_models() first.")
            
        print(f"Processing video: {video_path}")
        
        # Load video frames
        video_frames = self._load_video_frames(video_path)
        num_frames = len(video_frames)
        print(f"Loaded {num_frames} frames")
        
        # Initialize video tracking session
        print("Initializing video tracking session...")
        inference_session = self.video_processor.init_video_session(
            video=video_frames,
            inference_device=self.device,
            dtype=torch.bfloat16
        )
        
        # Detect initial objects on first frame using text prompts
        print(f"Detecting objects with prompts: {text_prompts}")
        first_frame = video_frames[0]
        if isinstance(first_frame, torch.Tensor):
            first_frame = first_frame.permute(1, 2, 0).cpu().numpy()
            first_frame = (first_frame * 255).astype(np.uint8)
            
        initial_detections = self.detect_with_text(
            first_frame, 
            text_prompts[0], 
            threshold=detection_threshold
        )
        
        print(f"Found {len(initial_detections)} objects in first frame")
        
        if len(initial_detections) == 0:
            print("No objects detected in first frame. Trying more frames...")
            # Try a few more frames
            for frame_idx in [10, 30, 60]:
                if frame_idx < num_frames:
                    frame = video_frames[frame_idx]
                    if isinstance(frame, torch.Tensor):
                        frame = frame.permute(1, 2, 0).cpu().numpy()
                        frame = (frame * 255).astype(np.uint8)
                    detections = self.detect_with_text(frame, text_prompts[0], threshold=detection_threshold)
                    if detections:
                        initial_detections = detections
                        print(f"Found {len(detections)} objects at frame {frame_idx}")
                        break
        
        # Add detected objects to tracking session using their centroids as point prompts
        tracked_objects = {}
        
        for i, detection in enumerate(initial_detections):
            obj_id = i + 1
            cx, cy = detection['centroid']
            
            # Add point prompt for this object
            self.video_processor.add_inputs_to_inference_session(
                inference_session=inference_session,
                frame_idx=0,
                obj_ids=obj_id,
                input_points=[[[[cx, cy]]]],
                input_labels=[[[1]]]  # 1 = positive click
            )
            
            tracked_objects[obj_id] = {
                'id': obj_id,
                'initial_detection': detection,
                'trajectory': [],
                'confidence': detection['confidence'],
                'label': detection['label']
            }
            
        print(f"Tracking {len(tracked_objects)} objects through video...")
        
        # Propagate tracking through entire video
        video_segments = {}
        
        for output in self.video_model.propagate_in_video_iterator(
            inference_session,
            show_progress_bar=True
        ):
            frame_idx = output.frame_idx
            masks = self.video_processor.post_process_masks(
                [output.pred_masks],
                original_sizes=[[inference_session.video_height, inference_session.video_width]],
                binarize=True
            )[0]
            
            video_segments[frame_idx] = {
                obj_id: masks[i].cpu().numpy()
                for i, obj_id in enumerate(inference_session.obj_ids)
            }
            
            # Update trajectories
            for i, obj_id in enumerate(inference_session.obj_ids):
                if obj_id in tracked_objects:
                    mask = masks[i].cpu().numpy()
                    # Get centroid from mask
                    if mask.sum() > 0:
                        y_coords, x_coords = np.where(mask > 0.5)
                        cx = x_coords.mean()
                        cy = y_coords.mean()
                        area = mask.sum()
                        tracked_objects[obj_id]['trajectory'].append({
                            'frame': frame_idx,
                            'centroid': [float(cx), float(cy)],
                            'area': float(area)
                        })
        
        # Summary
        print(f"\n✓ Video processing complete!")
        print(f"  Tracked {len(tracked_objects)} unique objects")
        print(f"  Processed {num_frames} frames")
        
        return {
            'num_frames': num_frames,
            'unique_objects': len(tracked_objects),
            'objects': tracked_objects,
            'segments': video_segments
        }

    def _load_video_frames(self, video_path: str, max_frames: int = None) -> List:
        """Load video frames from file."""
        from transformers.video_utils import load_video
        
        # Try using transformers video utility first
        try:
            frames, _ = load_video(video_path)
            if max_frames and len(frames) > max_frames:
                # Subsample frames
                indices = np.linspace(0, len(frames) - 1, max_frames, dtype=int)
                frames = [frames[i] for i in indices]
            return frames
        except Exception as e:
            print(f"Transformers video load failed: {e}")
            print("Falling back to OpenCV...")
        
        # Fallback to OpenCV
        cap = cv2.VideoCapture(video_path)
        frames = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(frame_rgb))
            
            if max_frames and len(frames) >= max_frames:
                break
                
        cap.release()
        return frames


class SAM3VideoPotholeDetector:
    """High-level pothole detector using SAM3 video tracking."""
    
    def __init__(self, sam_video_model: SAM3VideoModel):
        self.sam_model = sam_video_model
        self.pothole_prompts = [
            "pothole",
            "road damage", 
            "asphalt crack",
            "pavement hole"
        ]
        
    def detect_potholes_in_video(
        self,
        video_path: str,
        confidence_threshold: float = 0.5,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        Detect and track potholes throughout a video.
        
        Each unique pothole is detected once and tracked, eliminating duplicates.
        
        Args:
            video_path: Path to drone video
            confidence_threshold: Minimum confidence for detection
            output_dir: Directory to save results
            
        Returns:
            Dictionary with unique potholes and their tracks
        """
        results = self.sam_model.process_video(
            video_path=video_path,
            text_prompts=self.pothole_prompts,
            detection_threshold=confidence_threshold,
            output_dir=output_dir
        )
        
        # Filter and enhance results
        potholes = []
        for obj_id, obj_data in results['objects'].items():
            if obj_data['trajectory']:  # Only include objects that were actually tracked
                pothole = {
                    'pothole_id': f"pothole_{obj_id:03d}",
                    'confidence': obj_data['confidence'],
                    'first_frame': obj_data['trajectory'][0]['frame'] if obj_data['trajectory'] else 0,
                    'last_frame': obj_data['trajectory'][-1]['frame'] if obj_data['trajectory'] else 0,
                    'frames_visible': len(obj_data['trajectory']),
                    'initial_bbox': obj_data['initial_detection']['bbox'],
                    'label': obj_data['label']
                }
                potholes.append(pothole)
                
        return {
            'video_path': video_path,
            'num_frames': results['num_frames'],
            'unique_potholes': len(potholes),
            'potholes': potholes,
            'raw_results': results
        }
