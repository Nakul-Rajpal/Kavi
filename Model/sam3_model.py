"""
SAM3 Model Wrapper for Pothole Detection
Handles loading and inference with the Segment Anything Model 3
"""

import torch
import numpy as np
from typing import List, Dict, Tuple, Optional
import cv2


class SAM3Model:
    """Wrapper class for SAM3 model operations"""

    def __init__(self, model_type: str = "vit_h", checkpoint_path: Optional[str] = None, device: str = "cuda"):
        """
        Initialize SAM3 model

        Args:
            model_type: Model architecture type (vit_h, vit_l, vit_b)
            checkpoint_path: Path to SAM3 checkpoint file
            device: Device to run model on ('cuda' or 'cpu')
        """
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model_type = model_type
        self.checkpoint_path = checkpoint_path
        self.model = None
        self.predictor = None

        print(f"Initializing SAM3 on device: {self.device}")

    def load_model(self):
        """Load SAM3 model and predictor"""
        try:
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor

            # Build SAM3 model
            self.model = build_sam2(
                config_file=f"sam2_hiera_{self.model_type}.yaml",
                ckpt_path=self.checkpoint_path,
                device=self.device
            )

            # Initialize predictor
            self.predictor = SAM2ImagePredictor(self.model)
            print("SAM3 model loaded successfully")
            return True

        except Exception as e:
            print(f"Error loading SAM3 model: {e}")
            print("Note: Make sure to install SAM2 package and download checkpoints")
            return False

    def set_image(self, image: np.ndarray):
        """
        Set image for segmentation

        Args:
            image: Input image as numpy array (RGB format)
        """
        if self.predictor is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        self.predictor.set_image(image)

    def predict_masks(
        self,
        point_coords: Optional[np.ndarray] = None,
        point_labels: Optional[np.ndarray] = None,
        box: Optional[np.ndarray] = None,
        mask_input: Optional[np.ndarray] = None,
        multimask_output: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate segmentation masks

        Args:
            point_coords: Nx2 array of point prompts
            point_labels: N array of labels (1=foreground, 0=background)
            box: Bounding box in xyxy format
            mask_input: Low-res mask from previous prediction
            multimask_output: Whether to return multiple masks

        Returns:
            Tuple of (masks, scores, logits)
        """
        if self.predictor is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        masks, scores, logits = self.predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            box=box,
            mask_input=mask_input,
            multimask_output=multimask_output
        )

        return masks, scores, logits

    def segment_everything(self, image: np.ndarray) -> List[Dict]:
        """
        Perform automatic mask generation on entire image

        Args:
            image: Input image as numpy array (RGB format)

        Returns:
            List of segmentation results with masks and metadata
        """
        try:
            from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator

            # Initialize automatic mask generator
            mask_generator = SAM2AutomaticMaskGenerator(
                model=self.model,
                points_per_side=32,
                pred_iou_thresh=0.86,
                stability_score_thresh=0.92,
                crop_n_layers=1,
                crop_n_points_downscale_factor=2,
                min_mask_region_area=100
            )

            # Generate masks
            masks = mask_generator.generate(image)
            return masks

        except Exception as e:
            print(f"Error in automatic segmentation: {e}")
            return []

    def reset(self):
        """Reset predictor state"""
        if self.predictor:
            self.predictor.reset_image()


class SAM3PotholeDetector:
    """SAM3-based pothole detector with automatic segmentation"""

    def __init__(self, sam_model: SAM3Model):
        """
        Initialize pothole detector

        Args:
            sam_model: Initialized SAM3Model instance
        """
        self.sam_model = sam_model

    def detect_potholes(self, image: np.ndarray, confidence_threshold: float = 0.5) -> List[Dict]:
        """
        Detect potholes in image using SAM3 segmentation

        Args:
            image: Input image (RGB format)
            confidence_threshold: Minimum confidence for pothole detection

        Returns:
            List of detected potholes with masks and metadata
        """
        # Generate all segments in the image
        all_segments = self.sam_model.segment_everything(image)

        # Filter segments that likely represent potholes
        pothole_candidates = []

        for segment in all_segments:
            # Extract segment features
            features = self._extract_segment_features(segment, image)

            # Classify if segment is a pothole
            is_pothole, confidence = self._classify_pothole(features)

            if is_pothole and confidence >= confidence_threshold:
                pothole_candidates.append({
                    'mask': segment['segmentation'],
                    'bbox': segment['bbox'],
                    'area': segment['area'],
                    'confidence': confidence,
                    'features': features
                })

        return pothole_candidates

    def _extract_segment_features(self, segment: Dict, image: np.ndarray) -> Dict:
        """
        Extract features from segmented region

        Args:
            segment: Segment dictionary from SAM3
            image: Original image

        Returns:
            Dictionary of extracted features
        """
        mask = segment['segmentation']
        bbox = segment['bbox']  # [x, y, w, h]

        # Calculate shape features
        area = segment['area']
        aspect_ratio = bbox[2] / max(bbox[3], 1)

        # Extract color features from masked region
        masked_region = cv2.bitwise_and(image, image, mask=mask.astype(np.uint8))
        mean_color = cv2.mean(image, mask=mask.astype(np.uint8))[:3]

        # Texture features (simplified)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        masked_gray = cv2.bitwise_and(gray, gray, mask=mask.astype(np.uint8))
        texture_variance = np.var(masked_gray[mask > 0]) if np.any(mask) else 0

        return {
            'area': area,
            'aspect_ratio': aspect_ratio,
            'mean_color': mean_color,
            'texture_variance': texture_variance,
            'bbox': bbox
        }

    def _classify_pothole(self, features: Dict) -> Tuple[bool, float]:
        """
        Classify if features indicate a pothole

        Args:
            features: Extracted features dictionary

        Returns:
            Tuple of (is_pothole, confidence)
        """
        # Heuristic-based classification (can be replaced with ML model)
        confidence = 0.0

        # Potholes are typically:
        # 1. Dark colored (low brightness)
        # 2. Irregular shape (moderate aspect ratio)
        # 3. Moderate size
        # 4. High texture variance (rough surface)

        brightness = np.mean(features['mean_color'])

        # Score based on darkness (potholes are usually darker than road)
        if brightness < 100:
            confidence += 0.3
        elif brightness < 150:
            confidence += 0.15

        # Score based on size (typical pothole size range)
        area = features['area']
        if 500 < area < 50000:
            confidence += 0.25
        elif 100 < area < 100000:
            confidence += 0.1

        # Score based on aspect ratio (not too elongated)
        aspect_ratio = features['aspect_ratio']
        if 0.3 < aspect_ratio < 3.0:
            confidence += 0.2

        # Score based on texture (rough surface)
        if features['texture_variance'] > 200:
            confidence += 0.25
        elif features['texture_variance'] > 100:
            confidence += 0.15

        is_pothole = confidence >= 0.5

        return is_pothole, min(confidence, 1.0)
