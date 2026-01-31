# Kavi

This repository contains two projects:

1. **Pothole Detection with SAM3** - Automated pothole detection from drone video
2. **Live Ping Map** - Real-time location visualization with Supabase

---

## Live Ping Map

A real-time location ping visualization app built with React, Vite, and Supabase Realtime.

### Features

- Real-time ping updates via Supabase Realtime (postgres_changes)
- Interactive map with OpenStreetMap tiles
- Emoji markers with popup details
- Auto-fly to new pings
- Connection status indicator
- Responsive design

### Prerequisites

- Node.js 18+
- npm or yarn
- Supabase project with Realtime enabled

### Quick Start

#### 1. Install dependencies

```bash
npm install
```

#### 2. Run the development server

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Supabase Setup

The database is configured with the following:

#### Table: `pings`

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid | Primary key (auto-generated) |
| `lat` | double precision | Latitude coordinate |
| `lng` | double precision | Longitude coordinate |
| `created_at` | timestamptz | Timestamp (auto-generated) |

### Testing

To test real-time updates, insert a new ping directly in Supabase:

```sql
INSERT INTO pings (lat, lng) VALUES (42.3736, -72.5199);
```

### Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool
- **Supabase** - Backend (Postgres + Realtime)
- **react-leaflet** - Map components
- **Leaflet** - Map library
- **OpenStreetMap** - Tile provider

---

## Pothole Detection with SAM3

Automated pothole detection from drone video using Meta's SAM3 (Segment Anything Model 3) with GPS telemetry integration.

### Quick Start

#### 1. Request SAM3 Access
- Visit: https://huggingface.co/facebook/sam3-large
- Click "Request Access"
- Wait for approval (instant to a few hours)

#### 2. Install Dependencies
```bash
cd Model
python3.11 -m pip install torch torchvision opencv-python pillow transformers huggingface-hub requests pandas tqdm
```

#### 3. Authenticate
```bash
# Get token from https://huggingface.co/settings/tokens
python3.11 -c "from huggingface_hub import login; login()"
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

# Live stream (webcam)
python3.11 main.py 0 --live
```

Results saved to `./results/` with JSON, CSV, and annotated images.

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

### Available Models

| Model | Size | Speed | Use Case |
|-------|------|-------|----------|
| `facebook/sam3-large` | ~3GB | Slow | Production (best accuracy) |
| `facebook/sam3-base-plus` | ~1GB | Medium | Balanced |
| `facebook/sam3-base` | ~400MB | Fast | Testing |
| `facebook/sam3-small` | ~200MB | Fastest | Real-time |

### System Requirements

- Python 3.8+
- PyTorch 2.1.0+
- Transformers 4.47.0+
- NVIDIA GPU recommended (CPU works but slower)

---

## Project Structure

```
Kavi/
├── README.md
├── package.json            # Live Ping Map dependencies
├── vite.config.js
├── index.html
├── src/                    # Live Ping Map React app
│   ├── main.jsx
│   ├── App.jsx
│   ├── index.css
│   ├── lib/
│   │   └── supabaseClient.js
│   └── components/
│       └── PingMap.jsx
└── Model/                  # Pothole Detection
    ├── sam3_model.py
    ├── pothole_detector.py
    ├── video_processor.py
    ├── telemetry_handler.py
    ├── results_reporter.py
    ├── main.py
    ├── test_sam3.py
    └── requirements.txt
```
