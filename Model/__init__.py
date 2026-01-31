"""
Kavi Pothole Detection System
SAM3-based pothole detection from drone footage
"""

from .sam3_model import SAM3Model, SAM3PotholeDetector
from .video_processor import VideoProcessor, FrameProcessor
from .telemetry_handler import TelemetryHandler, TelemetryData
from .pothole_detector import PotholeDetectionPipeline, PotholeDetection
from .results_reporter import (
    ResultsReporter,
    WebSocketReporter,
    LocalFileReporter,
    MultiReporter
)
from .config import (
    ModelConfig,
    VideoConfig,
    DetectionConfig,
    TelemetryConfig,
    ReportingConfig,
    PipelineConfig,
    DEFAULT_CONFIG
)

__version__ = "1.0.0"

__all__ = [
    # Models
    'SAM3Model',
    'SAM3PotholeDetector',

    # Video Processing
    'VideoProcessor',
    'FrameProcessor',

    # Telemetry
    'TelemetryHandler',
    'TelemetryData',

    # Detection Pipeline
    'PotholeDetectionPipeline',
    'PotholeDetection',

    # Reporting
    'ResultsReporter',
    'WebSocketReporter',
    'LocalFileReporter',
    'MultiReporter',

    # Configuration
    'ModelConfig',
    'VideoConfig',
    'DetectionConfig',
    'TelemetryConfig',
    'ReportingConfig',
    'PipelineConfig',
    'DEFAULT_CONFIG',
]
