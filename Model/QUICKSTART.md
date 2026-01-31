# Quick Start Guide

Get up and running with Kavi Pothole Detection in 5 minutes!

## Step 1: Install Dependencies

```bash
cd Model

# Install PyTorch (CUDA 11.8)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install SAM2
pip install git+https://github.com/facebookresearch/segment-anything-2.git

# Install other requirements
pip install -r requirements.txt
```

## Step 2: Download SAM3 Checkpoint

```bash
# Download SAM2 checkpoint (example - check Meta's repo for latest)
wget https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_large.pt
```

Or download from: https://github.com/facebookresearch/segment-anything-2

## Step 3: Run Your First Detection

```bash
# Basic usage (replace paths with your files)
python main.py /path/to/your/drone_video.mp4 \
    --checkpoint sam2_hiera_large.pt \
    --output ./results

# With telemetry data
python main.py /path/to/your/drone_video.mp4 \
    --checkpoint sam2_hiera_large.pt \
    --telemetry /path/to/telemetry.srt \
    --output ./results
```

## Step 4: Check Results

Results are saved to `./results/` directory:
- `detections.json` - All detections in JSON format
- `detections.csv` - CSV format for spreadsheet analysis
- `frame_XXXXXX_detected.jpg` - Annotated frames with detected potholes

## Quick Test with Webcam

```bash
# Test with your webcam (live demo)
python main.py 0 \
    --checkpoint sam2_hiera_large.pt \
    --live \
    --confidence 0.6 \
    --process-every-n 15
```

## Python API Example

```python
from Model import SAM3Model, PotholeDetectionPipeline

# Load model
sam = SAM3Model(checkpoint_path="sam2_hiera_large.pt", device="cuda")
sam.load_model()

# Create pipeline
pipeline = PotholeDetectionPipeline(
    sam_model=sam,
    video_source="drone_video.mp4",
    confidence_threshold=0.5
)

# Process video
detections = pipeline.process_video(output_dir="./results", save_frames=True)

# Print results
print(f"Found {len(detections)} potholes!")
```

## Common Issues

### CUDA Out of Memory
```bash
# Process fewer frames
python main.py video.mp4 --checkpoint checkpoint.pt --process-every-n 10
```

### Slow Processing
```bash
# Use CPU mode (slower but no GPU needed)
# Edit main.py and change device="cuda" to device="cpu"
```

### No Detections
```bash
# Lower confidence threshold
python main.py video.mp4 --checkpoint checkpoint.pt --confidence 0.3
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [example_usage.py](example_usage.py) for more examples
- Configure API endpoint for UI integration
- Add telemetry data for GPS-tagged detections

## File Structure

```
Model/
├── main.py              # Main entry point
├── example_usage.py     # Example scripts
├── requirements.txt     # Dependencies
├── README.md           # Full documentation
└── results/            # Output directory (created automatically)
```

## Support

For issues, check:
1. SAM2 repository: https://github.com/facebookresearch/segment-anything-2
2. README.md troubleshooting section
3. example_usage.py for working examples
