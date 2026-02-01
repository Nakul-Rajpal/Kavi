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
        output_dir: Optional[str] = None,
        max_frames: int = 300,
        frame_skip: int = 5
    ) -> Dict:
        """
        Process entire video for pothole detection.
        Runs detection on ALL frames and deduplicates to find unique potholes.
        
        Args:
            video_path: Path to video file
            text_prompts: Text prompts for initial detection
            detection_threshold: Confidence threshold for detection
            detection_frame_interval: Run text detection every N frames to find new objects
            output_dir: Directory to save results
            max_frames: Maximum frames to process (for memory efficiency)
            frame_skip: Process every Nth frame (e.g., 5 = every 5th frame)
            
        Returns:
            Dictionary with tracked objects and their trajectories
        """
        if self.image_model is None:
            raise RuntimeError("Models not loaded. Call load_models() first.")
            
        print(f"Processing video: {video_path}")
        print(f"  Frame skip: every {frame_skip} frames")
        print(f"  Max frames: {max_frames}")
        
        # Load video frames with subsampling
        video_frames, fps, frame_mapping = self._load_video_frames(video_path, max_frames=max_frames, frame_skip=frame_skip)
        num_frames = len(video_frames)
        print(f"Loaded {num_frames} frames (subsampled)")
        
        # Run detection on ALL frames throughout the video
        print(f"Running detection on all {num_frames} frames with prompts: {text_prompts}")
        
        # Store all detections with their frame info
        all_detections = []  # List of (frame_idx, detection)
        tracked_objects = {}
        next_obj_id = 1
        video_segments = {}
        
        # Distance threshold for considering two detections as the same pothole
        # This accounts for camera movement between frames
        DEDUP_DISTANCE_THRESHOLD = 150  # pixels
        
        for frame_idx in range(num_frames):
            frame = video_frames[frame_idx]
            if isinstance(frame, torch.Tensor):
                frame = frame.permute(1, 2, 0).cpu().numpy()
                frame = (frame * 255).astype(np.uint8)
            elif isinstance(frame, Image.Image):
                frame = np.array(frame)
            
            # Detect potholes in this frame
            frame_detections = self.detect_with_text(frame, text_prompts[0], threshold=detection_threshold)
            
            new_in_frame = 0
            matched_in_frame = 0
            
            for detection in frame_detections:
                cx, cy = detection['centroid']
                
                # Check if this detection matches any existing tracked object
                best_match = None
                best_dist = float('inf')
                
                for obj_id, obj_data in tracked_objects.items():
                    # Check against all positions in trajectory (not just last)
                    # This helps with objects that temporarily disappear
                    for traj_point in obj_data['trajectory']:
                        prev_cx, prev_cy = traj_point['centroid']
                        dist = ((cx - prev_cx)**2 + (cy - prev_cy)**2) ** 0.5
                        if dist < best_dist:
                            best_dist = dist
                            best_match = obj_id
                
                if best_match and best_dist < DEDUP_DISTANCE_THRESHOLD:
                    # This is an existing pothole - update its trajectory
                    tracked_objects[best_match]['trajectory'].append({
                        'frame': frame_idx,
                        'centroid': [float(cx), float(cy)],
                        'area': detection['area']
                    })
                    # Update confidence if this detection is higher
                    if detection['confidence'] > tracked_objects[best_match]['confidence']:
                        tracked_objects[best_match]['confidence'] = detection['confidence']
                        tracked_objects[best_match]['best_detection'] = detection
                        tracked_objects[best_match]['best_frame_idx'] = frame_idx
                    matched_in_frame += 1
                else:
                    # This is a NEW pothole - create new tracked object
                    obj_id = next_obj_id
                    next_obj_id += 1
                    
                    tracked_objects[obj_id] = {
                        'id': obj_id,
                        'initial_detection': detection,
                        'best_detection': detection,
                        'best_frame_idx': frame_idx,
                        'first_frame_idx': frame_idx,
                        'trajectory': [{
                            'frame': frame_idx,
                            'centroid': [float(cx), float(cy)],
                            'area': detection['area']
                        }],
                        'confidence': detection['confidence'],
                        'label': detection['label']
                    }
                    new_in_frame += 1
                
                # Store segment info
                video_segments[frame_idx] = video_segments.get(frame_idx, {})
            
            if frame_idx % 10 == 0 or frame_idx == num_frames - 1:
                print(f"  Frame {frame_idx + 1}/{num_frames}: {len(frame_detections)} detections "
                      f"({new_in_frame} new, {matched_in_frame} matched) - "
                      f"Total unique: {len(tracked_objects)}")
        
        # Summary
        print(f"\n✓ Video processing complete!")
        print(f"  Tracked {len(tracked_objects)} unique objects")
        print(f"  Processed {num_frames} frames")
        
        return {
            'num_frames': num_frames,
            'unique_objects': len(tracked_objects),
            'objects': tracked_objects,
            'segments': video_segments,
            'video_frames': video_frames,
            'fps': fps,
            'frame_mapping': frame_mapping
        }

    def _load_video_frames(self, video_path: str, max_frames: int = 300, frame_skip: int = 5) -> Tuple[List, float, Dict[int, int]]:
        """
        Load frames from video, sampling evenly across the ENTIRE video duration.
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"  Video: {total_frames} frames, {fps:.1f} FPS, {duration:.1f} seconds")
        
        # Simple: sample max_frames evenly across entire video
        num_samples = min(max_frames, total_frames)
        step = max(1, total_frames // num_samples)
        
        frame_indices = list(range(0, total_frames, step))[:num_samples]
        
        print(f"  Sampling {len(frame_indices)} frames (every {step} frames)")
        print(f"  Coverage: frame 0 to {frame_indices[-1]} ({frame_indices[-1]/fps:.1f}s of {duration:.1f}s)")
        
        frames = []
        frame_mapping = {}
        
        for i, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(frame_rgb))
                frame_mapping[i] = frame_idx
                
        cap.release()
        print(f"  Loaded {len(frames)} frames")
        return frames, fps, frame_mapping


class SAM3VideoPotholeDetector:
    """High-level pothole detector using SAM3 video tracking."""
    
    def __init__(self, sam_video_model: SAM3VideoModel):
        self.sam_model = sam_video_model
        self.pothole_prompts = [
            "pothole",
            "pothole in road",
            "road pothole",
            "hole in asphalt"
        ]
    
    def is_likely_manhole(self, frame: np.ndarray, bbox: List[float], mask: Optional[np.ndarray] = None) -> bool:
        """
        Check if a detection is likely a manhole/sewer cover rather than a pothole.
        
        Manholes have:
        - Uniform color/texture (metallic surface)
        - Regular, smooth edges
        - Often circular with aspect ratio ~1.0
        
        Args:
            frame: RGB frame as numpy array
            bbox: Bounding box [x, y, w, h]
            mask: Optional segmentation mask
            
        Returns:
            True if detection looks like a manhole (should be filtered out)
        """
        x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        
        # Ensure valid bbox
        if w <= 0 or h <= 0:
            return False
            
        # Ensure bbox is within frame bounds
        frame_h, frame_w = frame.shape[:2]
        x = max(0, min(x, frame_w - 1))
        y = max(0, min(y, frame_h - 1))
        x2 = min(x + w, frame_w)
        y2 = min(y + h, frame_h)
        
        if x2 <= x or y2 <= y:
            return False
        
        # Extract the region of interest
        roi = frame[y:y2, x:x2]
        
        if roi.size == 0:
            return False
        
        # Convert to grayscale for analysis
        if len(roi.shape) == 3:
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        else:
            gray_roi = roi
        
        # Check 1: Aspect ratio close to 1.0 (circular/square)
        aspect_ratio = w / h if h > 0 else 0
        is_square = 0.75 < aspect_ratio < 1.35
        
        # Check 2: Low texture variance (smooth metallic surface)
        # Manholes have uniform surfaces, potholes have rough/varied texture
        texture_std = np.std(gray_roi)
        is_uniform = texture_std < 35  # Low variance = uniform surface
        
        # Check 3: Edge analysis - manholes have clean, regular edges
        edges = cv2.Canny(gray_roi, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size if edges.size > 0 else 0
        has_clean_edges = 0.02 < edge_density < 0.15  # Moderate edge density
        
        # Check 4: Color analysis - manholes often have grayish metallic color
        if len(roi.shape) == 3:
            mean_color = np.mean(roi, axis=(0, 1))
            # Check if grayish (R, G, B similar values)
            color_std = np.std(mean_color)
            is_grayish = color_std < 15  # Low color variance = grayish
        else:
            is_grayish = False
        
        # Combine checks - if multiple indicators suggest manhole, filter it out
        manhole_score = sum([is_square, is_uniform, has_clean_edges, is_grayish])
        
        # Need at least 3 indicators to classify as manhole
        return manhole_score >= 3
        
    def detect_potholes_in_video(
        self,
        video_path: str,
        confidence_threshold: float = 0.5,
        output_dir: Optional[str] = None,
        max_frames: int = 300,
        frame_skip: int = 5
    ) -> Dict:
        """
        Detect and track potholes throughout a video.
        
        Each unique pothole is detected once and tracked, eliminating duplicates.
        Saves frame images for each detected pothole.
        
        Args:
            video_path: Path to drone video
            confidence_threshold: Minimum confidence for detection
            output_dir: Directory to save results (frame images will be saved here)
            max_frames: Maximum frames to process
            frame_skip: Process every Nth frame
            
        Returns:
            Dictionary with unique potholes and their tracks
        """
        results = self.sam_model.process_video(
            video_path=video_path,
            text_prompts=self.pothole_prompts,
            detection_threshold=confidence_threshold,
            output_dir=output_dir,
            max_frames=max_frames,
            frame_skip=frame_skip
        )
        
        video_frames = results.get('video_frames', [])
        fps = results.get('fps', 30.0)
        frame_mapping = results.get('frame_mapping', {})
        
        # Create frames subdirectory if output_dir is provided
        frames_dir = None
        if output_dir:
            frames_dir = Path(output_dir) / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
        
        # Filter and enhance results
        potholes = []
        filtered_manholes = 0
        
        for obj_id, obj_data in results['objects'].items():
            if obj_data['trajectory']:  # Only include objects that were actually tracked
                first_subsampled_frame = obj_data['trajectory'][0]['frame'] if obj_data['trajectory'] else 0
                last_subsampled_frame = obj_data['trajectory'][-1]['frame'] if obj_data['trajectory'] else 0
                
                # Use the frame with best confidence for the image
                best_frame_idx = obj_data.get('best_frame_idx', first_subsampled_frame)
                best_detection = obj_data.get('best_detection', obj_data['initial_detection'])
                
                # Get original video frame number
                original_frame_num = frame_mapping.get(best_frame_idx, best_frame_idx * frame_skip)
                
                # MANHOLE FILTER: Check if this detection looks like a manhole/sewer cover
                if best_frame_idx < len(video_frames):
                    frame_for_check = video_frames[best_frame_idx]
                    if isinstance(frame_for_check, Image.Image):
                        frame_np_check = np.array(frame_for_check)
                    else:
                        frame_np_check = frame_for_check
                    
                    bbox = best_detection['bbox']
                    mask = best_detection.get('mask', None)
                    
                    if self.is_likely_manhole(frame_np_check, bbox, mask):
                        filtered_manholes += 1
                        print(f"  Filtered out manhole-like detection: object {obj_id}")
                        continue  # Skip this detection
                
                pothole = {
                    'pothole_id': f"pothole_{obj_id:03d}",
                    'confidence': obj_data['confidence'],
                    'first_frame': first_subsampled_frame,
                    'last_frame': last_subsampled_frame,
                    'best_frame': best_frame_idx,
                    'original_frame_number': original_frame_num,
                    'frames_visible': len(obj_data['trajectory']),
                    'initial_bbox': best_detection['bbox'],
                    'label': obj_data['label'],
                    'image_filename': None
                }
                
                # Save frame image from the BEST detection frame (highest confidence)
                if frames_dir and best_frame_idx < len(video_frames):
                    frame_img = video_frames[best_frame_idx]
                    image_filename = f"pothole_{obj_id:03d}_frame_{original_frame_num}.jpg"
                    image_path = frames_dir / image_filename
                    
                    # Convert PIL Image to numpy for drawing bbox
                    frame_np = np.array(frame_img)
                    
                    # Draw bounding box on the frame using best detection's bbox
                    bbox = best_detection['bbox']
                    x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                    cv2.rectangle(frame_np, (x, y), (x + w, y + h), (0, 255, 0), 3)
                    
                    # Add label with confidence
                    label_text = f"Pothole {obj_id} ({obj_data['confidence']:.2f})"
                    cv2.putText(frame_np, label_text, (x, y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    
                    # Save as BGR for cv2
                    frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(str(image_path), frame_bgr)
                    
                    pothole['image_filename'] = image_filename
                    print(f"  Saved frame: {image_filename} (from frame {best_frame_idx}, conf={obj_data['confidence']:.2f})")
                
                potholes.append(pothole)
        
        if filtered_manholes > 0:
            print(f"\n  Filtered out {filtered_manholes} manhole/sewer detections")
        
        # Clear video frames from results to save memory (they're saved to disk now)
        results_without_frames = {k: v for k, v in results.items() if k != 'video_frames'}
                
        return {
            'video_path': video_path,
            'num_frames': results['num_frames'],
            'unique_potholes': len(potholes),
            'potholes': potholes,
            'fps': fps,
            'frame_skip': frame_skip,
            'raw_results': results_without_frames
        }
