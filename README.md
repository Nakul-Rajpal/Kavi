# Kavi - Pothole Detection with SAM3

Automated pothole detection from drone video using Meta's SAM3 (Segment Anything Model 3) with GPS telemetry integration.

---

## Quick Start

### 1. Request SAM3 Access
- Visit: https://huggingface.co/facebook/sam3-large
- Click "Request Access"
- Wait for approval (instant to a few hours)

### 2. Install Dependencies
```bash
cd Model
python3.11 -m pip install torch torchvision opencv-python pillow transformers huggingface-hub requests pandas tqdm
```

### 3. Authenticate
```bash
# Get token from https://huggingface.co/settings/tokens
python3.11 -c "from huggingface_hub import login; login()"
```

### 4. Test Installation
```bash
python3.11 test_sam3.py
```

### 5. Process Video
```bash
# Basic usage
python3.11 main.py your_video.mp4

# With GPS telemetry
python3.11 main.py video.mp4 --telemetry telemetry.srt

# Live stream (webcam)
python3.11 main.py 0 --live
```

Results saved to `./results/` with JSON, CSV, and annotated images.

---

## Usage

### Command Line Options

```bash
python3.11 main.py <video_source> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `video_source` | Video file path or camera index (0 for webcam) | Required |
| `--model` | HuggingFace model ID | `facebook/sam3-large` |
| `--telemetry` | Telemetry file (SRT/CSV/JSON) | None |
| `--output` | Output directory | `./results` |
| `--confidence` | Detection threshold (0-1) | `0.5` |
| `--process-every-n` | Process every Nth frame | `5` |
| `--live` | Live stream mode | False |
| `--api-endpoint` | API URL for results | None |
| `--api-key` | API key | None |

### Examples

```bash
# Use smaller/faster model
python3.11 main.py video.mp4 --model facebook/sam3-base

# Higher confidence threshold
python3.11 main.py video.mp4 --confidence 0.7

# Process every 10th frame (faster)
python3.11 main.py video.mp4 --process-every-n 10

# Send results to API
python3.11 main.py video.mp4 --api-endpoint https://api.example.com/detections --api-key YOUR_KEY
```

---

## Python API

```python
from Model import SAM3Model, SAM3PotholeDetector
import cv2

# Initialize SAM3
sam = SAM3Model(model_id="facebook/sam3-large")
sam.load_model()

# Create detector
detector = SAM3PotholeDetector(sam)

# Detect potholes
image = cv2.imread("road.jpg")
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

potholes = detector.detect_potholes(
    image,
    confidence_threshold=0.5,
    custom_prompts=["pothole", "road damage"]
)

print(f"Found {len(potholes)} potholes")
```

### Full Pipeline

```python
from Model import SAM3Model, PotholeDetectionPipeline

sam = SAM3Model(model_id="facebook/sam3-large")
sam.load_model()

pipeline = PotholeDetectionPipeline(
    sam_model=sam,
    video_source="drone_video.mp4",
    telemetry_file="telemetry.srt",
    confidence_threshold=0.5
)

detections = pipeline.process_video(output_dir="./results", save_frames=True)
summary = pipeline.get_detections_summary()
```

---

## Output Format

### JSON
```json
{
  "summary": {
    "total_detections": 15,
    "frames_with_potholes": 8,
    "average_confidence": 0.72
  },
  "detections": [
    {
      "detection_id": "pothole_000001",
      "frame_number": 42,
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

### Files Generated
- `detections.json` - Complete results
- `detections.csv` - Spreadsheet format
- `summary.json` - Statistics
- `frame_XXXXXX_detected.jpg` - Annotated frames

---

## Telemetry Formats

### SRT (DJI Drones)
```srt
1
00:00:00,000 --> 00:00:00,033
GPS (37.7749, -122.4194, 100.5)

2
00:00:00,033 --> 00:00:00,066
GPS (37.7750, -122.4195, 100.8)
```

### CSV
```csv
frame_number,timestamp,latitude,longitude,altitude
0,1609459200.0,37.7749,-122.4194,100.5
1,1609459200.033,37.7750,-122.4195,100.8
```

### JSON
```json
[
  {"frame_number": 0, "latitude": 37.7749, "longitude": -122.4194, "altitude": 100.5}
]
```

---

## Available Models

| Model | Size | Speed | Use Case |
|-------|------|-------|----------|
| `facebook/sam3-large` | ~3GB | Slow | Production (best accuracy) |
| `facebook/sam3-base-plus` | ~1GB | Medium | Balanced |
| `facebook/sam3-base` | ~400MB | Fast | Testing |
| `facebook/sam3-small` | ~200MB | Fastest | Real-time |

---

## Troubleshooting

### "Access to model is restricted"
Request access at https://huggingface.co/facebook/sam3-large

### "401 Unauthorized"
```bash
python3.11 -c "from huggingface_hub import login; login()"
```

### "CUDA out of memory"
Use smaller model or process fewer frames:
```bash
python3.11 main.py video.mp4 --model facebook/sam3-base --process-every-n 10
```

### "No detections found"
Lower confidence threshold:
```bash
python3.11 main.py video.mp4 --confidence 0.3
```

### Slow first run
Normal - downloads ~3GB model. Subsequent runs use cached model.

---

## System Requirements

- Python 3.8+
- PyTorch 2.1.0+
- Transformers 4.47.0+
- NVIDIA GPU recommended (CPU works but slower)

---

## Project Structure

```
Kavi/
├── README.md
└── Model/
    ├── sam3_model.py           # SAM3 wrapper
    ├── pothole_detector.py     # Detection pipeline
    ├── video_processor.py      # Video processing
    ├── telemetry_handler.py    # GPS handling
    ├── results_reporter.py     # Output/API integration
    ├── main.py                 # CLI interface
    ├── test_sam3.py            # Installation test
    └── requirements.txt
```

---

## Why SAM3?

SAM3 (November 2025) supports text-based prompts for detection:

```python
# Just describe what to find
prompts = ["pothole", "road damage", "asphalt crack"]
detections = sam.detect_with_text(image, prompts, threshold=0.5)
```

Previous versions required complex heuristics. SAM3 understands concepts directly.
