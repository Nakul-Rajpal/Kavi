# DJI Air 3S – Live Video Feed Setup for Kavi

This guide explains how to connect your **DJI Air 3S** live camera feed to Kavi for real-time pothole detection.

---

## Option 1: RTMP with DJI Fly (step-by-step)

Use this if you want to stream from **DJI Fly** to your computer with **no custom app**. Your RC/phone and PC must be on the **same Wi‑Fi**.

### Step 1: Start the RTMP server on your Mac

From the `Model` folder, run the helper script (it starts Docker RTMP and prints the URL for DJI Fly):

```bash
cd Model
chmod +x run_dji_live_rtmp.sh
./run_dji_live_rtmp.sh
```

**Or do it manually:**

```bash
# One-time: pull the image
docker pull alfg/nginx-rtmp

# Start server: 1935 = RTMP ingest, 8080 = HLS for the Kavi UI Live tab
docker run -d -p 1935:1935 -p 8080:80 --name kavi-rtmp alfg/nginx-rtmp
```

### Step 2: Get your computer’s IP

```bash
# Usually Wi‑Fi is en0
ipconfig getifaddr en0
```

Example result: `192.168.1.100`. Use this in the next step.

### Step 3: Set the stream URL in DJI Fly

1. Power on **Air 3S** and **remote controller**; open **DJI Fly** (on RC 2 screen or on your phone with RC-N3).
2. Go to **GO FLY** → **Transmission** → **Live Streaming Platforms** → **RTMP**.
3. Enter the RTMP address (replace `YOUR_PC_IP` with your Mac’s IP from Step 2):

   **If the app has ONE field (“RTMP Address”):**  
   Enter the full URL in that single field:
   ```text
   rtmp://YOUR_PC_IP:1935/stream/dji
   ```
   Example: `rtmp://192.168.1.100:1935/stream/dji`

   **If the app has TWO fields (RTMP address + Stream key):**
   - **RTMP address:** `rtmp://YOUR_PC_IP:1935/stream`  
     Example: `rtmp://192.168.1.100:1935/stream`
   - **Stream key:** `dji`

4. No space or slash at the end. Use the **exact** IP (e.g. from `ipconfig getifaddr en0`).
5. **Start** the stream in the app. Leave it running.

### Step 4: Run Kavi on the live feed

On your Mac (same machine as the RTMP server):

```bash
cd Model
python3.11 main.py "rtmp://localhost:1935/stream/dji" --live
```

To reduce CPU/GPU load (e.g. process every 10th frame):

```bash
python3.11 main.py "rtmp://localhost:1935/stream/dji" --live --process-every-n 10
```

Results are saved under `./results/`. Press **Ctrl+C** to stop.

**View the live feed in the Kavi UI:**  
Run the dashboard (`npm run dev` in the repo root), open [http://localhost:3000](http://localhost:3000), and click **Live** in the header. The Live tab shows the same DJI stream via HLS (port 8080). If the stream does not appear, see **"Stream works on device but not on webpage"** below.

---

## Quick start (once the stream is already running)

If the RTMP server is up and DJI Fly is already streaming:

```bash
cd Model
python3.11 main.py "rtmp://localhost:1935/stream/dji" --live
```

---

## DJI Air 3S Overview

| Spec | Details |
|------|---------|
| **Model** | DJI Air 3S |
| **Video transmission** | O4 (stable, low-latency link to RC) |
| **Controller** | DJI RC 2 (built-in screen) or DJI RC-N3 (phone/tablet) |
| **App** | DJI Fly (required for streaming) |
| **Camera** | Dual: wide 1-inch 50MP, medium tele 48MP; video up to 4K/120fps |

The Air 3S does **not** output raw USB video like some enterprise drones. You get the live view by streaming from the **DJI Fly app** (or a custom app using DJI Mobile SDK) to your computer.

---

## How You Can Get a Live Feed

Two main options:

1. **RTMP (recommended with DJI Fly)** – Use DJI Fly’s built-in “Live Streaming” to send the feed to a local RTMP server; Kavi reads from that server.
2. **RTSP (developer)** – If you use **DJI Mobile SDK (MSDK)** and build an app that exposes an RTSP server, Kavi can connect to that RTSP URL.

The code in this project supports both **RTSP** and **RTMP** URLs as the live video source.

---

## Option A: RTMP with DJI Fly (reference)

Same as **Option 1** above. The **alfg/nginx-rtmp** Docker image uses the app name **`stream`** and the stream key is the last path segment (we use **`dji`**).

- **Publish URL (for DJI Fly):** `rtmp://YOUR_PC_IP:1935/stream/dji`
- **Play URL (for Kavi on same PC):** `rtmp://localhost:1935/stream/dji`

If OpenCV can’t open RTMP on your build, see **RTMP → RTSP relay** below.

---

## Option B: RTSP (e.g. with DJI Mobile SDK)

If you have an **RTSP URL** (e.g. from a custom app using DJI MSDK that exposes the live view as RTSP):

```bash
cd Model
python3.11 main.py "rtsp://username:password@192.168.1.1:8554/streaming/live/1" --live
```

- Replace with your actual RTSP URL, username, password, IP, and path.
- Kavi uses the FFmpeg backend for RTSP and optional TCP transport for stability (see code).

---

## RTMP → RTSP relay (if OpenCV can’t open RTMP directly)

Some OpenCV builds don’t open `rtmp://` reliably. You can relay RTMP → RTSP and then point Kavi at the RTSP URL.

**Example with FFmpeg:** receive RTMP and expose as RTSP (using a tool like `rtsp-simple-proxy` or FFmpeg + an RTSP server). Then:

```bash
python3.11 main.py "rtsp://127.0.0.1:8554/dji" --live
```

(Exact port and path depend on your RTSP server config.)

---

## Code Changes for Live Stream URLs

The project is set up so that:

- **`video_source`** in live mode can be:
  - A **camera index** (e.g. `0` for default webcam).
  - An **RTSP URL** (e.g. `rtsp://...`).
  - An **RTMP URL** (e.g. `rtmp://...`).

- **`video_processor`** detects `rtsp://` and `rtmp://`, uses the FFmpeg backend, and applies stream-friendly options (e.g. TCP for RTSP, handling missing frame count for live streams).

- **`main.py`** with `--live` no longer requires a local file path, so you can pass a stream URL directly.

---

## Telemetry (optional)

For **GPS/altitude** with detections:

- If your workflow records **SRT** (or CSV/JSON) from the flight (e.g. from the SD card or a tool that converts DJI metadata), pass it with `--telemetry` when processing **recorded** video.
- For **live** runs, telemetry would require a separate source (e.g. MSDK app or a device that logs and exports SRT in real time). The current Kavi live pipeline can run without telemetry; you can add a telemetry file later for replay or post-processing.

---

## Quick reference (Option 1)

| Step | Action |
|------|--------|
| 1 | Start RTMP server: `docker run -d -p 1935:1935 --name kavi-rtmp alfg/nginx-rtmp` |
| 2 | Get PC IP: `ipconfig getifaddr en0`; RC/phone and PC on same Wi‑Fi. |
| 3 | DJI Fly: Transmission → RTMP → `rtmp://YOUR_PC_IP:1935/stream/dji` → Start stream. |
| 4 | Run: `python3.11 main.py "rtmp://localhost:1935/stream/dji" --live` |

---

### If DJI Fly says "Check RTMP address or stream key"

- **Two separate fields (Address + Stream key):**  
  - RTMP address: `rtmp://YOUR_MAC_IP:1935/stream`  
  - Stream key: `dji`
- **Single "RTMP Address" field:**  
  Use: `rtmp://YOUR_MAC_IP:1935/stream/dji` (no space or slash at the end).
- **Same Wi‑Fi:** Phone/RC and Mac on the same network; get Mac IP with `ipconfig getifaddr en0`.
- **Server running:** On Mac run `docker ps`; if `kavi-rtmp` is not listed, run `docker start kavi-rtmp` or start it with `docker run -d -p 1935:1935 -p 8080:80 --name kavi-rtmp alfg/nginx-rtmp`.
- **Firewall:** Allow incoming connections on port **1935** (Mac System Settings → Network → Firewall).
- **Typo:** Re-type the IP; do not add a trailing slash or space.

---

### If DJI Fly says "Livestream error" (or stream fails to start)

1. **Same Wi‑Fi**  
   The **remote controller (or phone)** must be on the **same Wi‑Fi network** as your Mac. If the RC uses the drone’s WiFi (e.g. for control), the *device running DJI Fly* (RC built-in screen or phone) must still be on your home/office Wi‑Fi so it can reach your Mac’s IP.  
   - On Mac: `ipconfig getifaddr en0` (or `en1`) → e.g. `192.168.1.100`  
   - That IP must be reachable from the device running DJI Fly.

2. **RTMP server must be running**  
   On your Mac:
   ```bash
   docker ps
   ```
   You should see `kavi-rtmp` (or the container you started). If not:
   ```bash
   docker start kavi-rtmp
   # or first time:
   docker run -d -p 1935:1935 -p 8080:80 --name kavi-rtmp alfg/nginx-rtmp
   ```

3. **Port 1935 open on the Mac**  
   - **Mac firewall:** System Settings → Network → Firewall → Options. Ensure "Block all incoming connections" is off, or add an allow rule for the app that needs port 1935 (e.g. Docker or "Python").  
   - **Router:** Usually no need to open 1935 to the internet; same‑network streaming only needs the Mac to accept connections on 1935 from the LAN.

4. **Use the correct URL format**  
   - **One field:** `rtmp://YOUR_MAC_IP:1935/stream/dji` (replace `YOUR_MAC_IP` with the Mac’s IP; no `https://`, no trailing `/` or space).  
   - **Two fields:** Address `rtmp://YOUR_MAC_IP:1935/stream`, Stream key `dji`.

5. **Try the other field style**  
   If you used one field and it fails, try two fields (address + stream key), or the other way around, depending on what your DJI Fly version shows.

6. **Mic permission (if prompted)**  
   Some DJI Fly builds ask for microphone access to start a live stream. You can allow it and mute the mic; the stream only needs the video.

7. **Ping the Mac from the RC/phone (if possible)**  
   If the device running DJI Fly can run a browser or terminal, try opening `http://YOUR_MAC_IP` (e.g. `http://192.168.1.100`). If that never loads, the device can’t reach the Mac (wrong network, firewall, or wrong IP).

---

## Troubleshooting

- **“Failed to open video source”** – Check that the RTMP/RTSP server is running, the URL is correct, and (for RTMP) the app has started streaming. For RTSP, try TCP: the code sets FFmpeg options for RTSP transport.
- **Delayed or choppy** – Use `--process-every-n 10` (or higher) to reduce CPU/GPU load; close other apps.
- **OpenCV + RTMP** – If your OpenCV build doesn't support RTMP, use an RTMP→RTSP relay and pass the RTSP URL to Kavi.

### Stream works on device but not on webpage

1. **HLS port 8080 must be exposed** – Run `docker ps` and check for `0.0.0.0:8080->80/tcp` on `kavi-rtmp`. If 8080 is missing, recreate: `docker rm -f kavi-rtmp` then `./Model/run_dji_live_rtmp.sh`.
2. **Test HLS** – With DJI Fly streaming, open `http://localhost:8080/live/dji_720p2628kbs/index.m3u8` on the Mac. If it downloads or shows playlist text, HLS works; refresh the Live tab.
3. **Viewing from another device** – The stream is on the Mac. Create `.env.local` with `NEXT_PUBLIC_LIVE_STREAM_URL=http://YOUR_MAC_IP:8080/live/dji_720p2628kbs/index.m3u8` (use Mac IP from `ipconfig getifaddr en0`), restart `npm run dev`, and open the UI at `http://YOUR_MAC_IP:3000`.
4. **Firewall** – Allow inbound on ports 8080 and 3000 if viewing from another device.

This setup is tailored to the **DJI Air 3S** used with **DJI Fly** and optional **MSDK/RTSP**; the same flow applies to other DJI consumer drones that support RTMP live streaming in the Fly app.
