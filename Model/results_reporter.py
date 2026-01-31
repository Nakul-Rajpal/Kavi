"""
Results Reporter for UI Integration
Sends pothole detection results to UI/API endpoint
"""

import json
import requests
from typing import List, Dict, Optional, Callable
import threading
import queue
from datetime import datetime
from pathlib import Path

from .pothole_detector import PotholeDetection


class ResultsReporter:
    """Report detection results to UI or external system"""

    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        batch_size: int = 10,
        enable_websocket: bool = False
    ):
        """
        Initialize results reporter

        Args:
            api_endpoint: API endpoint URL to send results
            api_key: API authentication key
            batch_size: Number of detections to batch before sending
            enable_websocket: Enable WebSocket for real-time updates
        """
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.batch_size = batch_size
        self.enable_websocket = enable_websocket

        self.detection_queue = queue.Queue()
        self.pending_detections: List[PotholeDetection] = []
        self.reporter_thread = None
        self.is_running = False

        # Statistics
        self.total_sent = 0
        self.total_failed = 0

    def start_background_reporting(self):
        """Start background thread for sending results"""
        if self.is_running:
            print("Reporter already running")
            return

        self.is_running = True
        self.reporter_thread = threading.Thread(target=self._reporting_loop, daemon=True)
        self.reporter_thread.start()
        print("Background reporting started")

    def _reporting_loop(self):
        """Background loop for sending results"""
        while self.is_running:
            try:
                # Get detection from queue (blocking with timeout)
                detection = self.detection_queue.get(timeout=1.0)
                self.pending_detections.append(detection)

                # Send batch if size reached
                if len(self.pending_detections) >= self.batch_size:
                    self._send_batch()

            except queue.Empty:
                # Check if there are pending detections to send
                if self.pending_detections:
                    self._send_batch()
                continue

    def _send_batch(self):
        """Send batch of detections to API"""
        if not self.pending_detections:
            return

        if not self.api_endpoint:
            # Just log if no endpoint configured
            print(f"Would send {len(self.pending_detections)} detections (no API endpoint configured)")
            self.pending_detections = []
            return

        try:
            # Prepare payload
            payload = {
                'timestamp': datetime.now().isoformat(),
                'detections': [d.to_dict() for d in self.pending_detections],
                'count': len(self.pending_detections)
            }

            # Set headers
            headers = {
                'Content-Type': 'application/json'
            }
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            # Send POST request
            response = requests.post(
                self.api_endpoint,
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                self.total_sent += len(self.pending_detections)
                print(f"Successfully sent {len(self.pending_detections)} detections to API")
            else:
                self.total_failed += len(self.pending_detections)
                print(f"Failed to send detections: {response.status_code} - {response.text}")

        except Exception as e:
            self.total_failed += len(self.pending_detections)
            print(f"Error sending detections to API: {e}")

        finally:
            self.pending_detections = []

    def report_detection(self, detection: PotholeDetection):
        """
        Report a single detection

        Args:
            detection: PotholeDetection object
        """
        if self.is_running:
            # Add to queue for background processing
            self.detection_queue.put(detection)
        else:
            # Send immediately
            self.pending_detections.append(detection)
            if len(self.pending_detections) >= self.batch_size:
                self._send_batch()

    def report_detections(self, detections: List[PotholeDetection]):
        """
        Report multiple detections

        Args:
            detections: List of PotholeDetection objects
        """
        for detection in detections:
            self.report_detection(detection)

    def flush(self):
        """Send any pending detections immediately"""
        if self.pending_detections:
            self._send_batch()

    def stop(self):
        """Stop background reporting and flush pending results"""
        self.is_running = False

        if self.reporter_thread:
            self.reporter_thread.join(timeout=5.0)

        # Flush any pending detections
        self.flush()

        print(f"Reporter stopped. Sent: {self.total_sent}, Failed: {self.total_failed}")

    def get_statistics(self) -> Dict:
        """Get reporting statistics"""
        return {
            'total_sent': self.total_sent,
            'total_failed': self.total_failed,
            'pending': len(self.pending_detections),
            'queued': self.detection_queue.qsize() if self.is_running else 0
        }


class WebSocketReporter:
    """Real-time WebSocket reporter for live detections"""

    def __init__(self, websocket_url: str):
        """
        Initialize WebSocket reporter

        Args:
            websocket_url: WebSocket server URL
        """
        self.websocket_url = websocket_url
        self.ws = None
        self.is_connected = False

    def connect(self):
        """Connect to WebSocket server"""
        try:
            import websocket

            self.ws = websocket.create_connection(self.websocket_url)
            self.is_connected = True
            print(f"Connected to WebSocket: {self.websocket_url}")
            return True

        except Exception as e:
            print(f"Failed to connect to WebSocket: {e}")
            self.is_connected = False
            return False

    def send_detection(self, detection: PotholeDetection):
        """
        Send detection via WebSocket

        Args:
            detection: PotholeDetection object
        """
        if not self.is_connected:
            print("WebSocket not connected")
            return

        try:
            message = {
                'type': 'pothole_detection',
                'data': detection.to_dict(),
                'timestamp': datetime.now().isoformat()
            }

            self.ws.send(json.dumps(message))

        except Exception as e:
            print(f"Error sending WebSocket message: {e}")
            self.is_connected = False

    def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.ws:
            self.ws.close()
            self.is_connected = False
            print("WebSocket disconnected")


class LocalFileReporter:
    """Save results to local files for later processing"""

    def __init__(self, output_dir: str):
        """
        Initialize local file reporter

        Args:
            output_dir: Directory to save results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create session directory
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / session_id
        self.session_dir.mkdir(exist_ok=True)

        self.detections_file = self.session_dir / "detections.jsonl"
        self.summary_file = self.session_dir / "summary.json"

        print(f"Saving results to: {self.session_dir}")

    def report_detection(self, detection: PotholeDetection):
        """
        Save detection to JSONL file

        Args:
            detection: PotholeDetection object
        """
        with open(self.detections_file, 'a') as f:
            f.write(detection.to_json() + '\n')

    def save_summary(self, summary: Dict):
        """
        Save summary to JSON file

        Args:
            summary: Summary dictionary
        """
        with open(self.summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"Summary saved to: {self.summary_file}")


class MultiReporter:
    """Combine multiple reporters for simultaneous output"""

    def __init__(self):
        """Initialize multi-reporter"""
        self.reporters: List = []

    def add_reporter(self, reporter):
        """Add a reporter"""
        self.reporters.append(reporter)

    def report_detection(self, detection: PotholeDetection):
        """Report to all reporters"""
        for reporter in self.reporters:
            try:
                reporter.report_detection(detection)
            except Exception as e:
                print(f"Error in reporter {type(reporter).__name__}: {e}")

    def report_detections(self, detections: List[PotholeDetection]):
        """Report multiple detections to all reporters"""
        for detection in detections:
            self.report_detection(detection)

    def flush(self):
        """Flush all reporters"""
        for reporter in self.reporters:
            if hasattr(reporter, 'flush'):
                reporter.flush()

    def stop(self):
        """Stop all reporters"""
        for reporter in self.reporters:
            if hasattr(reporter, 'stop'):
                reporter.stop()
