"""
Configuration settings for pothole detection system
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class ModelConfig:
    """SAM2 Model configuration"""
    model_type: str = "large"  # large, base_plus, small, or tiny
    checkpoint_path: Optional[str] = None
    device: str = "cuda"  # cuda or cpu
    use_automatic_mask_generation: bool = True


@dataclass
class VideoConfig:
    """Video processing configuration"""
    max_side: int = 720  # Cap frame longer side to this (keeps aspect ratio; helps avoid SAM3 shape errors)
    process_every_n_frames: int = 5  # Process every Nth frame (1 = all frames)
    buffer_size: int = 30  # Frame buffer size for live processing
    enable_enhancement: bool = True  # Enable image enhancement
    enable_denoising: bool = False  # Enable denoising (slower)


@dataclass
class DetectionConfig:
    """Pothole detection configuration"""
    confidence_threshold: float = 0.5  # Minimum confidence for detection
    min_pothole_area: int = 100  # Minimum area in pixels
    max_pothole_area: int = 100000  # Maximum area in pixels
    enable_nms: bool = True  # Non-maximum suppression for overlapping detections
    nms_threshold: float = 0.3  # IoU threshold for NMS


@dataclass
class ReportingConfig:
    """Results reporting configuration"""
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    batch_size: int = 10
    enable_websocket: bool = False
    websocket_url: Optional[str] = None
    save_to_file: bool = True
    output_dir: str = "./results"
    save_annotated_frames: bool = True


@dataclass
class DeduplicationConfig:
    """Deduplication configuration for tracking unique potholes across frames"""
    enabled: bool = True  # Enable deduplication
    iou_threshold: float = 0.15  # Min overlap to consider same pothole (0.0-1.0)
    centroid_threshold: float = 100.0  # Max centroid distance (pixels) to consider same pothole
    max_age_frames: int = 100  # Frames before pothole is "forgotten" (prevents false matches)


@dataclass
class PipelineConfig:
    """Complete pipeline configuration"""
    model: ModelConfig
    video: VideoConfig
    detection: DetectionConfig
    reporting: ReportingConfig
    deduplication: DeduplicationConfig

    @classmethod
    def default(cls) -> 'PipelineConfig':
        """Create default configuration"""
        return cls(
            model=ModelConfig(),
            video=VideoConfig(),
            detection=DetectionConfig(),
            reporting=ReportingConfig(),
            deduplication=DeduplicationConfig()
        )

    @classmethod
    def from_env(cls) -> 'PipelineConfig':
        """Create configuration from environment variables"""
        return cls(
            model=ModelConfig(
                model_type=os.getenv('SAM_MODEL_TYPE', 'large'),
                checkpoint_path=os.getenv('SAM_CHECKPOINT_PATH'),
                device=os.getenv('SAM_DEVICE', 'cuda')
            ),
            video=VideoConfig(
                max_side=int(os.getenv('VIDEO_MAX_SIDE', '720')),
                process_every_n_frames=int(os.getenv('PROCESS_EVERY_N_FRAMES', '5'))
            ),
            detection=DetectionConfig(
                confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.5'))
            ),
            reporting=ReportingConfig(
                api_endpoint=os.getenv('API_ENDPOINT'),
                api_key=os.getenv('API_KEY'),
                output_dir=os.getenv('OUTPUT_DIR', './results')
            ),
            deduplication=DeduplicationConfig(
                enabled=os.getenv('DEDUP_ENABLED', 'true').lower() == 'true',
                iou_threshold=float(os.getenv('DEDUP_IOU_THRESHOLD', '0.15')),
                centroid_threshold=float(os.getenv('DEDUP_CENTROID_THRESHOLD', '100.0')),
                max_age_frames=int(os.getenv('DEDUP_MAX_AGE_FRAMES', '100'))
            )
        )


# Default configuration
DEFAULT_CONFIG = PipelineConfig.default()
