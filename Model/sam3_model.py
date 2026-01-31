"""
SAM3 Model Wrapper for Pothole Detection
Handles loading and inference with the Segment Anything Model 3 (November 2025)
"""

import torch
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
import cv2
from PIL import Image


class SAM3Model:
    """Wrapper class for SAM3 model operations with concept-based prompts"""

    def __init__(self, model_id: str = "facebook/sam3", device: str = "cuda"):
        """
        Initialize SAM3 model

        Args:
            model_id: Hugging Face model ID (facebook/sam3-large, facebook/sam3-base, etc.)
            device: Preferred device ('cuda', 'mps', or 'cpu'). Auto-picks MPS on Apple Silicon.
        """
        # Prefer CUDA, then MPS (Apple Silicon), then CPU
        if device == "cuda" and torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"  # Apple M1/M2/M3 GPU (Metal)
        else:
            self.device = "cpu"
        self.model_id = model_id
        self.model = None
        self.processor = None

        print(f"Initializing SAM3 on device: {self.device}")
        print(f"Model: {self.model_id}")

    def load_model(self):
        """Load SAM3 model and processor from Hugging Face"""
        try:
            from transformers import Sam3Model as HFSam3Model, Sam3Processor

            print("Loading SAM3 from Hugging Face...")
            print("  First run downloads ~3.4GB (model.safetensors). This can take 10–30+ min.")
            print("  To see progress: check ~/.cache/huggingface/hub/ for growing files.")
            print("  For faster download: pip install hf_transfer && set HF_HUB_ENABLE_HF_TRANSFER=1")

            # Load processor and model (official API: .to(device), not device_map)
            self.processor = Sam3Processor.from_pretrained(self.model_id)
            self.model = HFSam3Model.from_pretrained(self.model_id).to(self.device)

            # Set model to eval mode
            self.model.eval()

            print(f"✓ SAM3 model loaded successfully")
            print(f"  Model: {self.model_id}")
            print(f"  Device: {self.device}")
            return True

        except ImportError as e:
            print(f"✗ Error: SAM3 dependencies not installed")
            print(f"  {e}")
            print("\nTo install SAM3:")
            print("  1. Install transformers: pip install transformers>=4.47.0")
            print("  2. Request access: https://huggingface.co/facebook/sam3")
            print("  3. Authenticate: huggingface-cli login")
            return False

        except Exception as e:
            print(f"✗ Error loading SAM3 model: {e}")
            print("\nTroubleshooting:")
            print("  - Ensure you have access approved on Hugging Face")
            print("  - Authenticate: huggingface-cli login")
            print("  - Check model ID:", self.model_id)
            return False

    def detect_with_text(
        self,
        image: Union[np.ndarray, Image.Image],
        text_prompts: Union[str, List[str]],
        threshold: float = 0.5
    ) -> List[Dict]:
        """
        Detect objects using text prompts (SAM3's main feature!)

        Args:
            image: Input image (RGB numpy array or PIL Image)
            text_prompts: Text description(s) of what to detect
                         e.g., "pothole", ["pothole", "road damage", "asphalt crack"]
            threshold: Confidence threshold for detection

        Returns:
            List of detection results with masks, boxes, and scores
        """
        if self.model is None or self.processor is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Convert numpy to PIL if needed
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        # Ensure text_prompts is a list
        if isinstance(text_prompts, str):
            text_prompts = [text_prompts]

        # SAM3 processor tokenizes with max_length=32; passing a list batches to N*32 tokens
        # and the DETR encoder expects a single 32-token sequence. Use one prompt per call.
        text_for_processor = text_prompts[0] if text_prompts else "object"

        # Process inputs (processor adds original_sizes for post-processing)
        inputs = self.processor(
            images=image,
            text=text_for_processor,
            return_tensors="pt"
        )
        # Move to device; keep original_sizes for post_process, don't pass to model
        target_sizes_raw = inputs.pop("original_sizes", None)
        inputs = {k: v.to(self.device) if hasattr(v, 'to') else v for k, v in inputs.items()}

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Post-process (official API: post_process_instance_segmentation)
        target_sizes = target_sizes_raw
        if target_sizes is not None and hasattr(target_sizes, "tolist"):
            target_sizes = target_sizes.tolist()
        if not target_sizes:
            target_sizes = [[image.height, image.width]]
        results = self.processor.post_process_instance_segmentation(
            outputs,
            threshold=threshold,
            mask_threshold=0.5,
            target_sizes=target_sizes
        )[0]

        # Convert to our format (results: masks, boxes, scores; no labels in API)
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
                bbox = [x1, y1, x2 - x1, y2 - y1]
                detections.append({
                    'mask': mask,
                    'bbox': bbox,
                    'area': float(np.sum(mask > 0.5)),
                    'confidence': sc,
                    'label': text_prompts[0] if text_prompts else "object"
                })

        return detections

    def segment_with_points(
        self,
        image: Union[np.ndarray, Image.Image],
        point_coords: List[List[float]],
        point_labels: Optional[List[int]] = None
    ) -> Dict:
        """
        Segment using point prompts

        Args:
            image: Input image
            point_coords: List of [x, y] coordinates
            point_labels: List of labels (1=foreground, 0=background)

        Returns:
            Segmentation result with mask
        """
        if self.model is None or self.processor is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Convert numpy to PIL if needed
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        # Default all points to foreground if not specified
        if point_labels is None:
            point_labels = [1] * len(point_coords)

        # Process inputs
        inputs = self.processor(
            images=image,
            input_points=[point_coords],
            input_labels=[point_labels],
            return_tensors="pt"
        ).to(self.device)

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Get the best mask
        masks = outputs.pred_masks[0].cpu().numpy()
        scores = outputs.iou_scores[0].cpu().numpy()

        best_idx = np.argmax(scores)

        return {
            'mask': masks[best_idx],
            'confidence': float(scores[best_idx])
        }


class SAM3PotholeDetector:
    """SAM3-based pothole detector using concept prompts"""

    def __init__(self, sam_model: SAM3Model):
        """
        Initialize pothole detector

        Args:
            sam_model: Initialized SAM3Model instance
        """
        self.sam_model = sam_model

        # Define pothole-related prompts
        self.pothole_prompts = [
            "pothole",
            "road damage",
            "asphalt crack",
            "pavement hole",
            "road defect"
        ]

    def detect_potholes(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.5,
        custom_prompts: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Detect potholes in image using SAM3 text prompts

        Args:
            image: Input image (RGB format)
            confidence_threshold: Minimum confidence for pothole detection
            custom_prompts: Optional custom text prompts to use

        Returns:
            List of detected potholes with masks and metadata
        """
        # Use custom prompts if provided, otherwise use defaults
        prompts = custom_prompts or self.pothole_prompts

        # Detect using text prompts - SAM3's superpower!
        detections = self.sam_model.detect_with_text(
            image=image,
            text_prompts=prompts,
            threshold=confidence_threshold
        )

        # Enhance detections with additional features
        enhanced_detections = []
        for detection in detections:
            # Extract additional features
            features = self._extract_segment_features(detection, image)

            # Merge features into detection
            detection['features'] = features

            # Apply additional filtering if needed
            if self._is_valid_pothole(detection):
                enhanced_detections.append(detection)

        return enhanced_detections

    def _extract_segment_features(self, detection: Dict, image: np.ndarray) -> Dict:
        """
        Extract additional features from detected segment

        Args:
            detection: Detection dictionary with mask
            image: Original image

        Returns:
            Dictionary of extracted features
        """
        mask = detection['mask']
        bbox = detection['bbox']  # [x, y, w, h]

        # Calculate shape features
        aspect_ratio = bbox[2] / max(bbox[3], 1)

        # Extract color features from masked region
        if len(mask.shape) == 2:
            mask_uint8 = (mask > 0.5).astype(np.uint8) * 255
        else:
            mask_uint8 = mask.astype(np.uint8)

        mean_color = cv2.mean(image, mask=mask_uint8)[:3]

        # Texture features (simplified)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        masked_gray = cv2.bitwise_and(gray, gray, mask=mask_uint8)
        texture_variance = np.var(masked_gray[mask_uint8 > 0]) if np.any(mask_uint8) else 0

        return {
            'aspect_ratio': aspect_ratio,
            'mean_color': mean_color,
            'texture_variance': texture_variance,
            'brightness': np.mean(mean_color)
        }

    def _is_valid_pothole(self, detection: Dict) -> bool:
        """
        Additional validation to filter out false positives

        Args:
            detection: Detection dictionary

        Returns:
            True if valid pothole, False otherwise
        """
        # Size filtering (remove very small or very large detections)
        area = detection['area']
        if area < 100 or area > 100000:
            return False

        # Aspect ratio filtering (remove very elongated objects)
        if 'features' in detection:
            aspect_ratio = detection['features']['aspect_ratio']
            if aspect_ratio < 0.2 or aspect_ratio > 5.0:
                return False

        return True

    def detect_with_examples(
        self,
        image: np.ndarray,
        example_images: List[np.ndarray],
        confidence_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Detect potholes using example images (SAM3 image exemplar feature)

        Args:
            image: Input image to search in
            example_images: List of example pothole images
            confidence_threshold: Minimum confidence threshold

        Returns:
            List of detected potholes
        """
        # Note: This would require additional implementation with SAM3's
        # image exemplar feature. For now, fall back to text prompts.
        print("Image exemplar detection not yet implemented. Using text prompts.")
        return self.detect_potholes(image, confidence_threshold)
