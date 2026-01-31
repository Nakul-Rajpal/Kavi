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

- Visit: https://huggingface.co/facebook/sam3-large
- Click "Request Access"
- Wait for approval

#### 2. Install Dependencies

```bash
cd Model
python3.11 -m pip install torch torchvision opencv-python pillow transformers huggingface-hub requests pandas tqdm
```

#### 3. Authenticate

```bash
python3.11 -c "from huggingface_hub import login; login()"
```

#### 4. Process Video

```bash
# Basic usage
python3.11 main.py your_video.mp4

# With GPS telemetry
python3.11 main.py video.mp4 --telemetry telemetry.srt
```

Results saved to `./results/` with JSON, CSV, and annotated images.

### Detection Categories

- Potholes
- Broken streetlights
- Traffic light damage
- Fallen trees
- Road debris
- Damaged street signs
- Flooding / standing water

---

## Project Structure

```
Kavi/
├── src/                    # Next.js Dashboard
│   ├── app/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── Map.tsx
│   │   ├── Header.tsx
│   │   ├── GlassPanel.tsx
│   │   ├── Timeline.tsx
│   │   ├── FilterMenu.tsx
│   │   └── DetectionsSidebar.tsx
│   └── styles/
│       └── globals.css
├── Model/                  # Pothole Detection
│   ├── sam3_model.py
│   ├── pothole_detector.py
│   ├── video_processor.py
│   ├── telemetry_handler.py
│   ├── results_reporter.py
│   └── main.py
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── README.md
```

## License

MIT
