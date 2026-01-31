# What We Did With the Model – Full Detail

This document explains how the SAM3 model is integrated into Kavi: what it is, how it’s loaded and run, what we changed, and how it fits into the pipeline.

---

## 1. What the model is

- **SAM3 (Segment Anything Model 3)** – Meta’s foundation model for **promptable segmentation** (November 2025). It can segment objects in images (and video) from:
  - **Text prompts** (e.g. “pothole”, “road damage”)
  - Point/box prompts
  - Image exemplars

- **Why we use it:** Pothole detection is framed as “segment everything that matches these text concepts.” We use the **text-prompt** API so we don’t need a separate object detector or custom training; we just prompt with “pothole”, “road damage”, etc.

- **Source:** Hugging Face `facebook/sam3` (gated; requires access + auth). One checkpoint, ~3.4 GB (`model.safetensors`), plus a small processor (tokenizer, image preprocessor).

---

## 2. Where it lives in the code

- **`sam3_model.py`** – Wrapper around Hugging Face’s SAM3:
  - **`SAM3Model`** – Loads the model and processor, runs **text-prompt detection** (`detect_with_text`) and optional point-based segmentation.
  - **`SAM3PotholeDetector`** – Uses `SAM3Model` with pothole-specific text prompts, optional feature extraction, and simple size/aspect-ratio filtering.

- **`pothole_detector.py`** – **`PotholeDetectionPipeline`** – Orchestrates:
  - Reading video (or live stream) → frames
  - Preprocessing/enhancement (resize, CLAHE, etc.)
  - Calling **`SAM3PotholeDetector.detect_potholes()`** on each (or every Nth) frame
  - Turning raw detections into **`PotholeDetection`** objects (with frame number, bbox, confidence, optional telemetry)
  - Exporting to JSON/CSV and saving annotated images

- **`main.py`** – CLI: parses arguments, builds the pipeline, runs either **video file** or **live stream** mode, and wires in reporters (file, optional API).

So: **model** → **pothole detector** → **pipeline** → **main**.

---

## 3. Model loading (what we did)

### 3.1 Device selection (CUDA → MPS → CPU)

- **Goal:** Use GPU when available: NVIDIA (CUDA) or Apple Silicon (Metal/MPS); otherwise CPU.
- **Implementation:** In `SAM3Model.__init__` we no longer only check `torch.cuda.is_available()`. We:
  1. If user asked for `cuda` and CUDA is available → use `"cuda"`.
  2. Else if **MPS is available** (`torch.backends.mps.is_available()`) → use `"mps"` (Apple M1/M2/M3).
  3. Else → use `"cpu"`.

So on your MacBook M1 Pro the model runs on **Metal (MPS)**, not CPU.

### 3.2 Hugging Face API and model ID

- **Model ID:** The project originally used `facebook/sam3-large`. The correct, existing model on the Hub is **`facebook/sam3`**. We changed the default and all references to **`facebook/sam3`** so downloads and loading succeed.

- **Loading API:** We use the official Transformers API:
  - **Processor:** `Sam3Processor.from_pretrained(model_id)` – handles image + text preprocessing.
  - **Model:** `HFSam3Model.from_pretrained(model_id).to(self.device)` – we **do not** use `device_map=...`; we use **`.to(device)`** so it works the same on CUDA, MPS, and CPU.

- **Caching:** Model and processor are downloaded once via Hugging Face Hub and cached under `~/.cache/huggingface/hub/`. Later runs use the cache (no re-download unless you clear it or change model ID).

### 3.3 Download-only script

- **`download_model.py`** – A small script that only:
  - Calls `Sam3Processor.from_pretrained("facebook/sam3")`
  - Calls `Sam3Model.from_pretrained("facebook/sam3")`  
  so the ~3.4 GB file is downloaded and cached. You can run this once (e.g. overnight or on a fast connection), then run the full pipeline later without waiting on the big download.

---

## 4. Inference: text-prompt detection (what we did)

### 4.1 Correct Transformers API

- The original code assumed an API that doesn’t match the current SAM3 implementation in Transformers. We aligned it with the **official docs** (e.g. `transformers` v5.0 model_doc/sam3):

  - **Post-processing:** We use **`post_process_instance_segmentation`** (not `post_process_object_detection`) with:
    - `threshold` (confidence)
    - `mask_threshold=0.5`
    - `target_sizes` from the processor’s **`original_sizes`** so masks/boxes are in original image coordinates.

  - **Inputs to the model:** The processor returns a batch with `original_sizes` and other keys. We **pop `original_sizes`** from the dict before passing the rest into `model(**inputs)` so the model doesn’t receive an unexpected key. We use `original_sizes` only for post-processing.

  - **Output format:** The post-processor returns per-image dicts with **`masks`**, **`boxes`**, **`scores`** (no `labels` in the API). We map these into our internal list of detections: each has `mask`, `bbox` (x, y, w, h), `area`, `confidence`, and we set `label` from the text prompt (e.g. first prompt) since the API doesn’t return label indices.

### 4.2 Single vs multiple text prompts

- For **one** text prompt we pass a string; for **several** we pass a list. The processor and model accept both; we keep the first prompt as the display label when building our detection list.

### 4.3 Our detection format

- Each detection we expose has:
  - **`mask`** – binary/numpy mask for the instance
  - **`bbox`** – [x, y, width, height] in image pixels
  - **`area`** – sum of mask (or thresholded mask) pixels
  - **`confidence`** – score from the model
  - **`label`** – e.g. `"pothole"` (from the prompt we used)

This is what **`SAM3PotholeDetector.detect_potholes()`** returns (after filtering).

---

## 5. Pothole detector layer (SAM3PotholeDetector)

- **Role:** Specialize SAM3 for “pothole-like” objects and reduce obvious false positives.

- **Text prompts:** We use a fixed list of prompts, e.g.:
  - `"pothole"`, `"road damage"`, `"asphalt crack"`, `"pavement hole"`, `"road defect"`  
  You can override with **`custom_prompts`** when calling `detect_potholes()`.

- **Flow:**  
  `detect_potholes(image, confidence_threshold, custom_prompts)`  
  → calls **`sam_model.detect_with_text(image, text_prompts, threshold)`**  
  → then for each raw detection we (optionally) compute **extra features** (aspect ratio, mean color, texture variance, brightness) and run **`_is_valid_pothole()`**.

- **Filtering (`_is_valid_pothole`):**
  - **Area:** Discard if `area < 100` or `area > 100_000` pixels.
  - **Aspect ratio:** Discard if aspect ratio is outside a reasonable range (e.g. 0.2–5.0) so we drop very elongated or tiny slivers.

So the “model” part here is: **SAM3 gives segments + scores; we keep only those that look like plausible potholes by size and shape.**

---

## 6. Pipeline and main (how the model is used end-to-end)

### 6.1 Video file mode

1. **`main.py`** parses CLI (e.g. `python3.11 -m Model.main video.mp4 --process-every-n 5`).
2. Builds **`SAM3Model`** (device auto-selected: CUDA / MPS / CPU), calls **`load_model()`**.
3. Builds **`PotholeDetectionPipeline`** with that model, video path, confidence, `process_every_n_frames`, etc.
4. **Pipeline:**
   - **VideoProcessor** opens the video and yields frames (optionally every Nth).
   - **FrameProcessor** resizes and enhances each frame (e.g. CLAHE, sharpening).
   - For each frame we call **`sam_detector.detect_potholes(enhanced, confidence_threshold)`** → that’s **SAM3 + text prompts + our filtering**.
   - We attach optional telemetry (from **TelemetryHandler**) and build **`PotholeDetection`** objects (id, frame number, timestamp, confidence, bbox, area, telemetry).
   - If requested, we draw boxes/masks on the frame and save it (e.g. `frame_XXXXXX_detected.jpg`).
5. At the end we write **detections.json**, **detections.csv**, **summary.json** and optionally annotated images under **`output_dir`** (e.g. `./results/<timestamp>/`).

So the model is used **once per processed frame** via **`SAM3PotholeDetector.detect_potholes()`**.

### 6.2 Live stream mode

- Same model and detector; the only difference is the **video source**:
  - **VideoProcessor** is given an **RTSP or RTMP URL** (e.g. from DJI Fly).
  - We use **FFmpeg** backend and stream-friendly options (e.g. RTSP over TCP) in **`video_processor.py`**.
  - Frames are read from the live stream in a loop; each (or every Nth) frame is preprocessed, enhanced, and passed to **`detect_potholes()`**.
  - Detections are again turned into **`PotholeDetection`** and sent to reporters (file, optional API).

So the **model and inference path are identical**; only the frame source (file vs live URL) changes.

### 6.3 Running as a package (relative imports)

- **`main.py`** and the rest of **`Model`** are written to run as the **`Model`** package (from the **repo root**), so that relative imports inside **`pothole_detector.py`**, **`results_reporter.py`**, etc. work.
- We run with **`python3.11 -m Model.main ...`** from the **Kavi** root (not `python3.11 main.py` from inside `Model/`). The **`run_dji_live_rtmp.sh`** script does the same: it `cd`s to the repo root and runs **`python3.11 -m Model.main "rtmp://..." --live`** so the package and relative imports resolve correctly.

---

## 7. Summary of code and config changes

| What | Before / issue | After / fix |
|------|----------------|------------|
| **Model ID** | `facebook/sam3-large` (wrong / missing) | **`facebook/sam3`** everywhere |
| **Loading** | `from_pretrained(..., device_map=self.device)` | **`from_pretrained(...).to(self.device)`** |
| **Post-processing** | `post_process_object_detection` | **`post_process_instance_segmentation`** with `mask_threshold`, `target_sizes` from `original_sizes` |
| **Model inputs** | Passed full processor output to model | **Pop `original_sizes`** before `model(**inputs)`; use `original_sizes` only for post-processing |
| **Output handling** | Expected `labels` in results | Results only have **masks, boxes, scores**; we set **label** from the text prompt |
| **Device** | Only CUDA or CPU | **CUDA → MPS (Apple) → CPU** so M1 Pro uses Metal |
| **Run from** | `main.py` from `Model/` caused relative-import errors | Run as **`python3.11 -m Model.main`** from repo root; **relative imports** in `main.py` (e.g. `from .sam3_model import ...`) |
| **Download** | Only by running full pipeline | **`download_model.py`** to pre-download and cache the model |
| **Docs / UX** | Slow download looked “stuck” | Messages in **`load_model()`** and **HUGGINGFACE_AUTH.md** about size, cache path, and **hf_transfer** |

---

## 8. Data flow (one frame)

```
Video (file or RTMP/RTSP)
  → VideoProcessor yields frame (RGB)
  → FrameProcessor: resize + enhance (e.g. CLAHE, sharpen)
  → SAM3PotholeDetector.detect_potholes(enhanced, confidence_threshold)
       → SAM3Model.detect_with_text(enhanced, ["pothole", "road damage", ...], threshold)
            → Sam3Processor(images=..., text=...)  → inputs
            → pop original_sizes; model(**inputs)  → raw outputs
            → post_process_instance_segmentation(..., target_sizes=original_sizes)
            → convert to list of {mask, bbox, area, confidence, label}
       → _extract_segment_features, _is_valid_pothole (filter by area, aspect ratio)
  → For each detection: PotholeDetection(detection_id, frame_number, timestamp, confidence, bbox, area, telemetry)
  → Optional: draw on frame, save image; append to pipeline.detections
  → At end: export detections.json, detections.csv, summary.json
```

So in full detail: **the model** is Hugging Face’s **SAM3** loaded with the correct ID and API, run on **CUDA or MPS or CPU**, with **text-prompt instance segmentation** and our **pothole-specific prompts and filtering**, inside a **video/live pipeline** that produces the structured detections and files you see in **`results/`**.
