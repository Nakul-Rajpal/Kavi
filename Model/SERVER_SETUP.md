# Running Kavi on a Server

You can run the pothole detection pipeline on a **remote server** (e.g. cloud VM) for faster model download, GPU inference, or to keep the drone/RC on the field while processing runs elsewhere.

---

## What you need on the server

- **OS:** Linux (Ubuntu 22.04 or similar) recommended.
- **Python:** 3.11 (or 3.9+).
- **GPU (optional but recommended):** NVIDIA GPU + CUDA for much faster SAM3 inference. Without GPU it runs on CPU (slower).
- **Network:** Outbound HTTPS (for Hugging Face). For **live stream from DJI Fly**, the server needs a **public IP** and **port 1935** open for RTMP.

---

## 1. One-time setup on the server

### Clone the repo and install dependencies

```bash
# Clone (or rsync/scp your Kavi folder)
git clone https://github.com/YOUR_USER/Kavi.git
cd Kavi
```

### Python and virtual env

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip  # or use pyenv

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### Install Model dependencies

**CPU only:**

```bash
cd Model
pip install -r requirements.txt
pip install hf-transfer   # optional: faster HF downloads
```

**With NVIDIA GPU (CUDA 12.x):**

```bash
cd Model
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
pip install hf-transfer
```

### Hugging Face auth on the server

Use a **Read** token so the server can download the model:

```bash
export HF_TOKEN="hf_your_token_here"
# Or one-time:
python3.11 -c "from huggingface_hub import login; login(token='hf_...')"
```

Optional: add `export HF_HUB_ENABLE_HF_TRANSFER=1` for faster downloads.

### Test

```bash
cd /path/to/Kavi
source .venv/bin/activate
python3.11 -m Model.test_sam3
```

---

## 2. Option A: Process video files on the server

Good when you record video on the drone and upload it later.

1. Copy a video file to the server (e.g. `scp`, `rsync`, or upload via a web UI).
2. Run:

```bash
cd /path/to/Kavi
source .venv/bin/activate
python3.11 -m Model.main /path/to/your_video.mp4 --output ./results
```

3. Download results from `./results/` (e.g. `scp -r server:~/Kavi/results ./`).

---

## 3. Option B: Live stream from DJI Fly to the server

Use this when you want the **server** to receive the RTMP stream from DJI Fly and run Kavi there.

### On the server

1. **Install Docker** (for RTMP server):

   ```bash
   sudo apt install -y docker.io
   sudo usermod -aG docker $USER
   # Log out and back in, or: newgrp docker
   ```

2. **Start the RTMP server** (binds to all interfaces so DJI Fly can reach it):

   ```bash
   docker run -d -p 1935:1935 --name kavi-rtmp alfg/nginx-rtmp
   ```

3. **Open port 1935** in the server firewall and (if applicable) cloud security group:
   - **UFW:** `sudo ufw allow 1935/tcp && sudo ufw reload`
   - **AWS/GCP/Azure:** Add inbound rule for TCP 1935 from 0.0.0.0/0 (or your IP only).

4. **Get the server’s public IP** (e.g. `curl -s ifconfig.me`).

### In DJI Fly (on your phone/RC)

1. **GO FLY** → **Transmission** → **Live Streaming** → **RTMP**.
2. **RTMP address:** `rtmp://SERVER_PUBLIC_IP:1935/stream`  
   **Stream key:** `dji`  
   Or single field: `rtmp://SERVER_PUBLIC_IP:1935/stream/dji`
3. Start the stream (mic plugged in if required).

### Run Kavi on the server

```bash
cd /path/to/Kavi
source .venv/bin/activate
python3.11 -m Model.main "rtmp://localhost:1935/stream/dji" --live --output ./results
```

The server receives the stream on port 1935 and Kavi reads it from `localhost`. Results go to `./results/` on the server; you can pull them with `scp` or expose them via an API/dashboard.

---

## 4. Option C: Run UI + Model on the same server

You can run the Next.js dashboard and the Model on one machine:

- **Dashboard:** `npm install && npm run build && npm start` (or use a process manager).
- **Model:** Run as above (video file or live RTMP).

Point the dashboard (or your app) at the server’s API or result files as needed.

---

## 5. Security notes

- **RTMP (port 1935):** If you open it to the internet, anyone who knows the URL could push a stream. Prefer restricting the firewall to your IP or a VPN.
- **HF_TOKEN:** Store it in the server environment (e.g. `.env` or a secrets manager), not in the repo.
- **Results:** If the server is public, protect the results directory or serve it only over HTTPS with auth.

---

## Quick reference

| Goal              | Command / step |
|-------------------|----------------|
| Install (GPU)     | `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121` then `pip install -r requirements.txt` |
| Auth              | `export HF_TOKEN="hf_..."` |
| Video file        | `python3.11 -m Model.main /path/to/video.mp4` |
| Live stream       | Server: RTMP on 1935, firewall open. DJI Fly → `rtmp://SERVER_IP:1935/stream/dji`. Run: `python3.11 -m Model.main "rtmp://localhost:1935/stream/dji" --live` |
| Results           | On server under `./results/`; pull with `scp` or your pipeline |
