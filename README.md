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
- **Live drone feed panel** – Click **Live** in the header to open the Live tab; it shows the DJI stream via HLS when the RTMP server is running and DJI Fly is streaming (see [DJI Air 3S setup](Model/DJI_AIR_3S_SETUP.md)).
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

### How it works (video → final output)

1. **You give it a video**  
   You run the program with a video file (e.g. `your_video.mp4`) or a live stream URL. Optionally you can pass a telemetry file (GPS per frame).

2. **It reads the video frame by frame**  
   The program opens the video and goes through it frame by frame. To save time, it can process only every 5th or 10th frame (you set this with `--process-every-n`).

3. **Each frame is prepared and sent to the AI**  
   For each frame it keeps, the program resizes it and does a bit of image improvement (contrast, sharpening). Then it sends that frame to the SAM3 model and asks: “Where are potholes (or road damage) in this image?”

4. **The AI returns detections**  
   The model returns regions it thinks are potholes: a box around each one, a mask (which pixels belong to it), and a confidence score. The program filters out very small or odd-shaped regions so you get fewer false alarms.

5. **Results are saved**  
   For every pothole found, the program records: frame number, position (box), confidence, and area. If you gave a telemetry file, it can attach GPS to each detection. At the end it writes:
   - **detections.json** – all detections in one structured file  
   - **detections.csv** – same data in spreadsheet form  
   - **summary.json** – counts and simple stats  
   - **Annotated images** – frames where potholes were found, with boxes (and optional masks) drawn on them  

   All of this goes into a timestamped folder under `./results/` (or whatever you set with `--output`).

So in short: **video in → frames → AI finds potholes → we save boxes, scores, and pictures.**

### Telemetry (GPS / location)

**What it is**  
Telemetry is location data from the drone (latitude, longitude, altitude, and sometimes heading/speed). It tells you *where* each frame was recorded, so you can attach a real-world position to each pothole.

**How you give it to the program**  
When you process a **recorded video** (not live stream), you can pass a telemetry file with `--telemetry`:

```bash
python3.11 -m Model.main your_video.mp4 --telemetry telemetry.srt
```

**Supported formats**

- **SRT** – Common with DJI drones (subtitle-style file with GPS lines).
- **CSV** – Columns like `frame_number`, `latitude`, `longitude`, `altitude`.
- **JSON** – List of objects with `frame_number` and position fields.

**How it’s used**  
The program loads the telemetry and matches it to video frames by **frame number**. If a frame doesn’t have an exact match, it uses the **nearest** frame’s telemetry (within a short range). Each pothole detection then gets that frame’s latitude, longitude, and altitude attached.

**Where it shows up**  
In **detections.json** and **detections.csv**, each detection has a `telemetry` (or latitude/longitude/altitude) field when telemetry was available for that frame. You can use that to plot detections on a map or report locations.

**Live stream**  
For live DJI Fly → RTMP, telemetry is not read from a file in the current setup; you’d need a separate source (e.g. an app that logs GPS in real time) to attach location during live runs.

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
