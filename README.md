# Kavi - Autonomous City Repair Detection

A cloud-based system where drones capture city footage, a vision pipeline detects infrastructure issues, and a modern web dashboard displays actionable tickets with location, severity, and status.

## Overview

**Kavi** consists of two main components:

1. **Dashboard UI** (Next.js) - A futuristic map-based dashboard showing drone detections
2. **Pothole Detection Model** (Python/SAM3) - Automated infrastructure issue detection from drone video

---

## Dashboard UI

A real-time visualization dashboard built with Next.js, React, and Leaflet.

### Features

- Interactive dark-themed map of Providence, RI
- Real-time detection markers with severity indicators
- Liquid glass UI design with modern aesthetics
- Live drone feed panel
- Historical timeline playback
- Filter by issue type, severity, and status

### Tech Stack

- **Next.js 14** - React framework
- **Tailwind CSS** - Styling
- **Leaflet** - Map visualization
- **Framer Motion** - Animations
- **Lucide React** - Icons

### Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Pothole Detection with SAM3

Automated pothole detection from drone video using Meta's SAM3 (Segment Anything Model 3) with GPS telemetry integration.

### Quick Start

#### 1. Request SAM3 Access

- Visit: https://huggingface.co/facebook/sam3
- Click "Request Access"
- Wait for approval

#### 2. Install Dependencies

```bash
cd Model
python3.11 -m pip install -r requirements.txt
```

#### 3. Authenticate

```bash
# Get token from https://huggingface.co/settings/tokens (type: Read)
python3.11 -c "from huggingface_hub import login; login()"
# Or: export HF_TOKEN="hf_your_token_here"
```

#### 4. Test Installation

```bash
python3.11 test_sam3.py
```

#### 5. Process Video

```bash
# Basic usage
python3.11 main.py your_video.mp4

# With GPS telemetry
python3.11 main.py video.mp4 --telemetry telemetry.srt

# Live stream (webcam or DJI Air 3S RTMP/RTSP)
python3.11 main.py 0 --live
# Or: python3.11 main.py "rtmp://localhost:1935/stream/dji" --live
```

Results saved to `./results/` with JSON, CSV, and annotated images.

### Command Line Options

```bash
python3.11 main.py <video_source> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `video_source` | Video file path, camera index (0), or RTSP/RTMP URL | Required |
| `--model` | HuggingFace model ID | `facebook/sam3` |
| `--telemetry` | Telemetry file (SRT/CSV/JSON) | None |
| `--output` | Output directory | `./results` |
| `--confidence` | Detection threshold (0-1) | `0.5` |
| `--process-every-n` | Process every Nth frame | `5` |
| `--live` | Live stream mode | False |
| `--api-endpoint` | API URL for results | None |
| `--api-key` | API key | None |

### DJI Air 3S Live Feed

See **Model/DJI_AIR_3S_SETUP.md** for Option 1 (RTMP with DJI Fly). Quick run:

```bash
cd Model && ./run_dji_live_rtmp.sh
```

### Available Models

| Model | Use Case |
|-------|----------|
| `facebook/sam3` | Production (gated, request access) |

### System Requirements

- Python 3.9+ (3.11 recommended)
- PyTorch 2.1.0+
- Transformers 5.0+ (for SAM3)
- NVIDIA GPU recommended (CPU works but slower)

---

## Project Structure

```
Kavi/
├── src/                    # Next.js Dashboard
│   ├── app/
│   ├── components/
│   └── styles/
├── Model/                  # Pothole Detection
│   ├── sam3_model.py
│   ├── pothole_detector.py
│   ├── video_processor.py
│   ├── telemetry_handler.py
│   ├── results_reporter.py
│   ├── main.py
│   ├── test_sam3.py
│   ├── DJI_AIR_3S_SETUP.md
│   ├── HUGGINGFACE_AUTH.md
│   ├── run_dji_live_rtmp.sh
│   └── requirements.txt
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── README.md
```

## License

MIT
