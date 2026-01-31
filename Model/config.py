"""
Configuration settings for pothole detection system
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class ModelConfig:
    """SAM3 Model configuration"""
    model_type: str = "vit_h"  # vit_h, vit_l, or vit_b
    checkpoint_path: Optional[str] = None
    device: str = "cuda"  # cuda or cpu
    use_automatic_mask_generation: bool = True


@dataclass
class VideoConfig:
    """Video processing configuration"""
    resize_height: int = 720  # Resize frames to this height
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
class TelemetryConfig:
    """Telemetry data configuration"""
    telemetry_file: Optional[str] = None
    telemetry_format: str = "srt"  # srt, csv, or json
    enable_interpolation: bool = True  # Interpolate missing telemetry


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
class PipelineConfig:
    """Complete pipeline configuration"""
    model: ModelConfig
    video: VideoConfig
    detection: DetectionConfig
    telemetry: TelemetryConfig
    reporting: ReportingConfig

    @classmethod
    def default(cls) -> 'PipelineConfig':
        """Create default configuration"""
        return cls(
            model=ModelConfig(),
            video=VideoConfig(),
            detection=DetectionConfig(),
            telemetry=TelemetryConfig(),
            reporting=ReportingConfig()
        )

    @classmethod
    def from_env(cls) -> 'PipelineConfig':
        """Create configuration from environment variables"""
        return cls(
            model=ModelConfig(
                model_type=os.getenv('SAM_MODEL_TYPE', 'vit_h'),
                checkpoint_path=os.getenv('SAM_CHECKPOINT_PATH'),
                device=os.getenv('SAM_DEVICE', 'cuda')
            ),
            video=VideoConfig(
                resize_height=int(os.getenv('VIDEO_RESIZE_HEIGHT', '720')),
                process_every_n_frames=int(os.getenv('PROCESS_EVERY_N_FRAMES', '5'))
            ),
            detection=DetectionConfig(
                confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.5'))
            ),
            telemetry=TelemetryConfig(
                telemetry_file=os.getenv('TELEMETRY_FILE')
            ),
            reporting=ReportingConfig(
                api_endpoint=os.getenv('API_ENDPOINT'),
                api_key=os.getenv('API_KEY'),
                output_dir=os.getenv('OUTPUT_DIR', './results')
            )
        )


# Default configuration
DEFAULT_CONFIG = PipelineConfig.default()
