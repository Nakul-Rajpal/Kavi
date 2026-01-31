"""
Video Processing Pipeline for Drone Footage
Handles video frame extraction and processing.
Supports files, camera index, and live stream URLs (RTSP/RTMP) for DJI and other drones.
"""

import os
import cv2
import numpy as np
from typing import Generator, Tuple, Optional, Dict
from pathlib import Path
import threading
import queue


def _is_stream_url(source: str) -> bool:
    """Return True if source is an RTSP or RTMP stream URL."""
    s = (source or "").strip().lower()
    return s.startswith("rtsp://") or s.startswith("rtmp://")


def _open_stream_capture(source: str):
    """
    Open RTSP/RTMP stream with FFmpeg backend and stream-friendly options.
    Uses TCP for RTSP when possible for more reliable drone feeds (e.g. DJI Air 3S).
    """
    # Prefer TCP for RTSP to avoid UDP packet loss on WiFi
    if source.strip().lower().startswith("rtsp://"):
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    return cap


class VideoProcessor:
    """Process video frames from drone footage (files, camera index, or RTSP/RTMP URLs)"""

    def __init__(self, video_source: str, buffer_size: int = 30):
        """
        Initialize video processor

        Args:
            video_source: Path to video file, camera index (e.g. 0), or stream URL (rtsp://... or rtmp://...)
            buffer_size: Size of frame buffer for live processing
        """
        self.video_source = video_source
        self.buffer_size = buffer_size
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.is_running = False
        self.capture_thread = None
        self._is_stream = _is_stream_url(str(video_source))

    def open_video(self) -> bool:
        """
        Open video source (file, camera index, or RTSP/RTMP URL).

        Returns:
            True if successful, False otherwise
        """
        try:
            if self._is_stream:
                self.cap = _open_stream_capture(self.video_source)
            else:
                self.cap = cv2.VideoCapture(self.video_source)
            if not self.cap.isOpened():
                print(f"Failed to open video source: {self.video_source}")
                return False

            # Get video properties
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if self._is_stream or self.total_frames <= 0:
                self.total_frames = 0
                print(f"Live stream opened: {self.frame_width}x{self.frame_height} @ {self.fps} FPS")
            else:
                print(f"Video opened: {self.frame_width}x{self.frame_height} @ {self.fps} FPS")
                print(f"Total frames: {self.total_frames}")

            return True

        except Exception as e:
            print(f"Error opening video: {e}")
            return False

    def process_frames(
        self,
        skip_frames: int = 0,
        max_frames: Optional[int] = None
    ) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        Generator that yields video frames

        Args:
            skip_frames: Number of frames to skip between processing
            max_frames: Maximum number of frames to process

        Yields:
            Tuple of (frame_number, frame_image)
        """
        if not hasattr(self, 'cap') or not self.cap.isOpened():
            if not self.open_video():
                return

        frame_count = 0
        processed_count = 0

        while True:
            ret, frame = self.cap.read()

            if not ret:
                break

            # Skip frames if specified
            if skip_frames > 0 and frame_count % (skip_frames + 1) != 0:
                frame_count += 1
                continue

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            yield frame_count, frame_rgb

            processed_count += 1
            frame_count += 1

            # Check if we've reached max frames
            if max_frames and processed_count >= max_frames:
                break

        self.close()

    def start_live_capture(self):
        """Start live video capture in separate thread"""
        if self.is_running:
            print("Capture already running")
            return

        if not self.open_video():
            return

        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        print("Live capture started")

    def _capture_loop(self):
        """Internal capture loop running in separate thread"""
        while self.is_running:
            ret, frame = self.cap.read()

            if not ret:
                print("End of video stream")
                self.is_running = False
                break

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            try:
                # Non-blocking put - drops frame if queue is full
                self.frame_queue.put_nowait(frame_rgb)
            except queue.Full:
                # Skip this frame if buffer is full
                pass

    def get_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Get next frame from live capture

        Args:
            timeout: Maximum time to wait for frame

        Returns:
            Frame as numpy array or None if timeout
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop_live_capture(self):
        """Stop live video capture"""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        self.close()
        print("Live capture stopped")

    def close(self):
        """Release video capture resources"""
        if hasattr(self, 'cap'):
            self.cap.release()


class FrameProcessor:
    """Process individual frames for pothole detection"""

    def __init__(self, resize_height: int = 720):
        """
        Initialize frame processor

        Args:
            resize_height: Target height for frame resizing (maintains aspect ratio)
        """
        self.resize_height = resize_height

    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for model input

        Args:
            frame: Input frame (RGB)

        Returns:
            Preprocessed frame
        """
        # Resize frame to reduce computation
        height, width = frame.shape[:2]

        if height > self.resize_height:
            scale = self.resize_height / height
            new_width = int(width * scale)
            frame = cv2.resize(frame, (new_width, self.resize_height))

        return frame

    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhance frame quality for better detection

        Args:
            frame: Input frame (RGB)

        Returns:
            Enhanced frame
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_RGB2LAB)

        # Apply CLAHE to L channel for contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])

        # Convert back to RGB
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

        # Apply slight sharpening
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        # Blend original and sharpened
        result = cv2.addWeighted(enhanced, 0.7, sharpened, 0.3, 0)

        return result

    def denoise_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Reduce noise in frame

        Args:
            frame: Input frame (RGB)

        Returns:
            Denoised frame
        """
        # Apply bilateral filter to reduce noise while preserving edges
        denoised = cv2.bilateralFilter(frame, 9, 75, 75)
        return denoised

    def annotate_detections(
        self,
        frame: np.ndarray,
        detections: list,
        show_masks: bool = True,
        show_boxes: bool = True
    ) -> np.ndarray:
        """
        Draw detection results on frame

        Args:
            frame: Input frame (RGB)
            detections: List of detection dictionaries
            show_masks: Whether to overlay masks
            show_boxes: Whether to draw bounding boxes

        Returns:
            Annotated frame
        """
        result = frame.copy()

        for i, detection in enumerate(detections):
            # Draw mask overlay
            if show_masks and 'mask' in detection:
                mask = detection['mask']
                color = np.array([255, 0, 0], dtype=np.uint8)  # Red color
                overlay = result.copy()
                overlay[mask > 0] = overlay[mask > 0] * 0.5 + color * 0.5
                result = overlay.astype(np.uint8)

            # Draw bounding box
            if show_boxes and 'bbox' in detection:
                x, y, w, h = detection['bbox']
                x, y, w, h = int(x), int(y), int(w), int(h)

                # Draw rectangle
                cv2.rectangle(result, (x, y), (x + w, y + h), (255, 0, 0), 2)

                # Draw confidence label
                confidence = detection.get('confidence', 0.0)
                label = f"Pothole {i+1}: {confidence:.2f}"

                # Add text background
                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(result, (x, y - text_h - 5), (x + text_w, y), (255, 0, 0), -1)

                # Add text
                cv2.putText(result, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX,
                           0.5, (255, 255, 255), 1)

        return result

    def save_annotated_frame(
        self,
        frame: np.ndarray,
        output_path: str,
        frame_number: int
    ):
        """
        Save annotated frame to disk

        Args:
            frame: Annotated frame (RGB)
            output_path: Directory to save frame
            frame_number: Frame number for filename
        """
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = output_dir / f"frame_{frame_number:06d}_detected.jpg"

        # Convert RGB to BGR for saving
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(filename), frame_bgr)
