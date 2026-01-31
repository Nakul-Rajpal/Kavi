# Kavi Pothole Detection System

SAM3-based automated pothole detection system for drone video footage with integrated telemetry data processing and real-time UI reporting.

## Overview

This system processes drone video footage to automatically detect and segment potholes using Meta's Segment Anything Model 3 (SAM3). It integrates telemetry data from the drone (GPS, altitude, heading, etc.) and reports results to a UI/API endpoint in real-time.

## Features

- **SAM3 Integration**: Leverages state-of-the-art segmentation model for accurate pothole detection
- **Video Processing**: Supports both recorded video files and live video streams
- **Telemetry Integration**: Processes drone telemetry data (GPS, altitude, heading, etc.) from SRT, CSV, or JSON formats
- **Real-time Detection**: Live stream processing with configurable frame skipping
- **Image Enhancement**: Automatic contrast enhancement and noise reduction
- **Multiple Output Formats**: JSON, CSV, and annotated video frames
- **API Integration**: Send results to REST API endpoints or WebSocket servers
- **Flexible Configuration**: Easy configuration through config files or environment variables

## Architecture

```
Model/
├── sam3_model.py          # SAM3 model wrapper and pothole detector
├── video_processor.py     # Video frame processing and annotation
├── telemetry_handler.py   # Drone telemetry data processing
├── pothole_detector.py    # Complete detection pipeline
├── results_reporter.py    # UI/API integration and reporting
├── config.py             # Configuration settings
├── main.py               # Main entry point
└── requirements.txt      # Python dependencies
```

## Installation

### 1. Prerequisites

- Python 3.8 or higher
- CUDA-capable GPU (recommended) or CPU
- FFmpeg (for video processing)

### 2. Install Dependencies

```bash
# Install PyTorch (adjust for your CUDA version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install SAM2 (SAM3)
pip install git+https://github.com/facebookresearch/segment-anything-2.git

# Install other requirements
cd Model
pip install -r requirements.txt
```

### 3. Download SAM3 Checkpoint

Download a SAM3 checkpoint from Meta:

```bash
# Example: Download SAM3 ViT-H checkpoint
wget https://dl.fbaipublicfiles.com/segment_anything_2/[checkpoint_name].pt
```

Available checkpoints:
- `sam2_hiera_large.pt` - Large model (best accuracy)
- `sam2_hiera_base_plus.pt` - Base+ model (balanced)
- `sam2_hiera_small.pt` - Small model (fastest)
- `sam2_hiera_tiny.pt` - Tiny model (most efficient)

## Usage

### Basic Video Processing

```bash
python main.py /path/to/drone_video.mp4 \
    --checkpoint /path/to/sam3_checkpoint.pt \
    --output ./results
```

### With Telemetry Data

```bash
python main.py /path/to/drone_video.mp4 \
    --checkpoint /path/to/sam3_checkpoint.pt \
    --telemetry /path/to/telemetry.srt \
    --output ./results
```

### With API Integration

```bash
python main.py /path/to/drone_video.mp4 \
    --checkpoint /path/to/sam3_checkpoint.pt \
    --api-endpoint https://your-api.com/detections \
    --api-key YOUR_API_KEY \
    --output ./results
```

### Live Stream Processing

```bash
python main.py 0 \
    --checkpoint /path/to/sam3_checkpoint.pt \
    --live \
    --api-endpoint https://your-api.com/detections \
    --confidence 0.6 \
    --process-every-n 10
```

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `video_source` | Path to video file or camera index | Required |
| `--checkpoint` | Path to SAM3 checkpoint file | Required |
| `--telemetry` | Path to telemetry file (SRT/CSV/JSON) | None |
| `--output` | Output directory for results | `./results` |
| `--api-endpoint` | API endpoint URL | None |
| `--api-key` | API authentication key | None |
| `--confidence` | Detection confidence threshold (0-1) | `0.5` |
| `--process-every-n` | Process every Nth frame | `5` |
| `--live` | Enable live stream mode | False |

## Python API Usage

### Example: Process Video File

```python
from Model import SAM3Model, PotholeDetectionPipeline, ResultsReporter

# Initialize SAM3 model
sam_model = SAM3Model(
    model_type="vit_h",
    checkpoint_path="./sam3_checkpoint.pt",
    device="cuda"
)
sam_model.load_model()

# Create detection pipeline
pipeline = PotholeDetectionPipeline(
    sam_model=sam_model,
    video_source="./drone_video.mp4",
    telemetry_file="./telemetry.srt",
    confidence_threshold=0.5,
    process_every_n_frames=5
)

# Process video
detections = pipeline.process_video(
    output_dir="./results",
    save_frames=True
)

# Get summary
summary = pipeline.get_detections_summary()
print(f"Found {summary['total_detections']} potholes")
```

### Example: Live Stream with Callback

```python
def on_detection(detections, frame):
    """Called when potholes are detected"""
    for det in detections:
        print(f"Pothole detected: {det.confidence:.2f} confidence")
        # Send to UI, trigger alert, etc.

pipeline.process_live_stream(
    callback_func=on_detection,
    output_dir="./live_results"
)
```

### Example: Custom Reporter

```python
from Model import MultiReporter, ResultsReporter, LocalFileReporter

# Create multi-reporter
reporter = MultiReporter()

# Add API reporter
api_reporter = ResultsReporter(
    api_endpoint="https://api.example.com/potholes",
    api_key="your_key",
    batch_size=10
)
reporter.add_reporter(api_reporter)

# Add file reporter
file_reporter = LocalFileReporter("./results")
reporter.add_reporter(file_reporter)

# Report detections
reporter.report_detections(detections)
```

## Telemetry File Formats

### SRT Format (DJI Drones)

```srt
1
00:00:00,000 --> 00:00:00,033
GPS (37.7749, -122.4194, 100.5)

2
00:00:00,033 --> 00:00:00,066
GPS (37.7750, -122.4195, 100.8)
```

### CSV Format

```csv
frame_number,timestamp,latitude,longitude,altitude,heading,speed
0,1609459200.0,37.7749,-122.4194,100.5,45.0,5.2
1,1609459200.033,37.7750,-122.4195,100.8,45.5,5.3
```

### JSON Format

```json
[
  {
    "frame_number": 0,
    "timestamp": 1609459200.0,
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 100.5,
    "heading": 45.0,
    "speed": 5.2
  }
]
```

## Output Format

### Detection Results (JSON)

```json
{
  "summary": {
    "total_detections": 15,
    "frames_with_potholes": 8,
    "average_confidence": 0.72,
    "detections_with_gps": 15
  },
  "detections": [
    {
      "detection_id": "pothole_000001",
      "frame_number": 42,
      "timestamp": 1609459200.0,
      "confidence": 0.85,
      "bbox": [120, 340, 80, 60],
      "area": 4800,
      "telemetry": {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 100.5
      }
    }
  ]
}
```

## Configuration

### Using Config File

```python
from Model import PipelineConfig, ModelConfig, DetectionConfig

config = PipelineConfig(
    model=ModelConfig(
        model_type="vit_h",
        checkpoint_path="./checkpoint.pt",
        device="cuda"
    ),
    detection=DetectionConfig(
        confidence_threshold=0.6,
        min_pothole_area=200
    )
)
```

### Using Environment Variables

```bash
export SAM_MODEL_TYPE=vit_h
export SAM_CHECKPOINT_PATH=/path/to/checkpoint.pt
export CONFIDENCE_THRESHOLD=0.6
export API_ENDPOINT=https://api.example.com
export API_KEY=your_key

python main.py video.mp4 --checkpoint $SAM_CHECKPOINT_PATH
```

## Performance Optimization

### GPU Acceleration

- Use CUDA-enabled GPU for best performance
- Process fewer frames: `--process-every-n 10`
- Use smaller SAM3 model: `vit_b` or `vit_l`

### CPU Mode

```python
sam_model = SAM3Model(device="cpu")
```

### Frame Processing

```python
from Model import VideoConfig

config = VideoConfig(
    resize_height=480,  # Lower resolution
    process_every_n_frames=10,  # Skip frames
    enable_enhancement=False  # Disable enhancement
)
```

## API Integration

### REST API Endpoint

Your API should accept POST requests with this format:

```json
{
  "timestamp": "2024-01-31T12:00:00",
  "count": 5,
  "detections": [
    {
      "detection_id": "pothole_000001",
      "confidence": 0.85,
      "bbox": [120, 340, 80, 60],
      "telemetry": {
        "latitude": 37.7749,
        "longitude": -122.4194
      }
    }
  ]
}
```

### WebSocket Integration

```python
from Model import WebSocketReporter

ws_reporter = WebSocketReporter("ws://your-server.com/ws")
ws_reporter.connect()
ws_reporter.send_detection(detection)
```

## Troubleshooting

### CUDA Out of Memory

- Reduce frame size: `--process-every-n 10`
- Use smaller model: download `vit_b` checkpoint
- Lower resolution in `VideoConfig`

### Slow Processing

- Skip more frames: `--process-every-n 30`
- Disable enhancement: set `enable_enhancement=False`
- Use GPU instead of CPU

### No Detections Found

- Lower confidence threshold: `--confidence 0.3`
- Check video quality and lighting
- Ensure road surface is visible

## License

This project uses Meta's SAM2 model, which is licensed under Apache 2.0.

## Citation

If you use this system, please cite:

```bibtex
@article{ravi2024sam2,
  title={SAM 2: Segment Anything in Images and Videos},
  author={Ravi, Nikhila and others},
  journal={arXiv preprint arXiv:2408.00714},
  year={2024}
}
```

## Support

For issues and questions:
- Check the troubleshooting section
- Review SAM2 documentation: https://github.com/facebookresearch/segment-anything-2
- Open an issue on GitHub
