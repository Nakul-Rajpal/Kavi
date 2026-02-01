"""
Complete Pothole Detection Pipeline
Integrates SAM3, video processing, and deduplication
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from .sam3_model import SAM3Model, SAM3PotholeDetector
from .video_processor import VideoProcessor, FrameProcessor
from .deduplication import PotholeTracker


@dataclass
class PotholeDetection:
    """Complete pothole detection result"""
    detection_id: str
    frame_number: int
    timestamp: float
    confidence: float
    bbox: List[float]  # [x, y, w, h]
    area: float
    image_path: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class PotholeDetectionPipeline:
    """Complete pipeline for pothole detection from drone video"""

    def __init__(
        self,
        sam_model: SAM3Model,
        video_source: str,
        confidence_threshold: float = 0.5,
        process_every_n_frames: int = 1,
        enable_deduplication: bool = True,
        dedup_iou_threshold: float = 0.15,
        dedup_centroid_threshold: float = 100.0,
        dedup_max_age_frames: int = 100
    ):
        """
        Initialize detection pipeline

        Args:
            sam_model: Initialized SAM3Model
            video_source: Path to video file or camera index
            confidence_threshold: Minimum confidence for pothole detection
            process_every_n_frames: Process every Nth frame (1 = process all frames)
            enable_deduplication: Whether to deduplicate detections across frames
            dedup_iou_threshold: IoU threshold for considering two detections the same
            dedup_centroid_threshold: Max centroid distance (pixels) to consider same pothole
            dedup_max_age_frames: Frames before a tracked pothole is forgotten
        """
        self.sam_detector = SAM3PotholeDetector(sam_model)
        self.video_processor = VideoProcessor(video_source)
        self.frame_processor = FrameProcessor()

        self.confidence_threshold = confidence_threshold
        self.process_every_n_frames = process_every_n_frames
        
        # Deduplication settings
        self.enable_deduplication = enable_deduplication
        self.tracker = PotholeTracker(
            iou_threshold=dedup_iou_threshold,
            centroid_threshold=dedup_centroid_threshold,
            max_age_frames=dedup_max_age_frames,
            min_confidence=confidence_threshold
        ) if enable_deduplication else None

        self.detections: List[PotholeDetection] = []
        self.detection_counter = 0
        self.total_raw_detections = 0  # Count before deduplication

    def process_video(
        self,
        output_dir: Optional[str] = None,
        save_frames: bool = False,
        max_frames: Optional[int] = None
    ) -> List[PotholeDetection]:
        """
        Process entire video for pothole detection

        Args:
            output_dir: Directory to save results
            save_frames: Whether to save annotated frames
            max_frames: Maximum number of frames to process

        Returns:
            List of pothole detections (deduplicated if enabled)
        """
        print("Starting video processing...")
        if self.enable_deduplication:
            print("Deduplication ENABLED (IoU-based tracking)")
        else:
            print("Deduplication DISABLED")
            
        self.detections = []
        self.total_raw_detections = 0
        
        if self.tracker:
            self.tracker.reset()

        for frame_num, frame in self.video_processor.process_frames(
            skip_frames=self.process_every_n_frames - 1,
            max_frames=max_frames
        ):
            # Preprocess frame
            preprocessed = self.frame_processor.preprocess_frame(frame)
            enhanced = self.frame_processor.enhance_frame(preprocessed)

            # Detect potholes
            potholes = self.sam_detector.detect_potholes(
                enhanced,
                confidence_threshold=self.confidence_threshold
            )
            
            # Track raw detection count
            self.total_raw_detections += len(potholes)

            # Apply deduplication if enabled
            if self.enable_deduplication and self.tracker:
                # Only get NEW unique potholes (not seen before)
                unique_potholes = self.tracker.update(potholes, frame_num)
                
                # Process only new unique detections
                for pothole in unique_potholes:
                    detection = self._create_detection(
                        frame_num=frame_num,
                        pothole=pothole
                    )
                    self.detections.append(detection)
            else:
                # No deduplication - process all detections
                for pothole in potholes:
                    detection = self._create_detection(
                        frame_num=frame_num,
                        pothole=pothole
                    )
                    self.detections.append(detection)

            # Save annotated frame if requested (use all potholes for visualization)
            if save_frames and output_dir and len(potholes) > 0:
                annotated = self.frame_processor.annotate_detections(
                    enhanced, potholes
                )
                self.frame_processor.save_annotated_frame(
                    annotated, output_dir, frame_num
                )

            # Progress update
            if frame_num % 100 == 0:
                if self.enable_deduplication:
                    print(f"Processed frame {frame_num}, {self.total_raw_detections} raw -> {len(self.detections)} unique potholes")
                else:
                    print(f"Processed frame {frame_num}, found {len(self.detections)} potholes so far")

        # Final summary
        if self.enable_deduplication:
            print(f"\nProcessing complete!")
            print(f"  Raw detections: {self.total_raw_detections}")
            print(f"  Unique potholes: {len(self.detections)}")
            print(f"  Deduplication ratio: {self.total_raw_detections / max(len(self.detections), 1):.1f}x")
        else:
            print(f"\nProcessing complete! Found {len(self.detections)} potholes total")
            
        return self.detections

    def process_live_stream(
        self,
        callback_func: Optional[callable] = None,
        output_dir: Optional[str] = None
    ):
        """
        Process live video stream

        Args:
            callback_func: Function to call with detection results
            output_dir: Directory to save frames with detections
        """
        print("Starting live video processing...")
        print(f"  Confidence threshold: {self.confidence_threshold}")
        print(f"  Process every {self.process_every_n_frames} frame(s)")
        if self.enable_deduplication:
            print("Deduplication ENABLED (IoU-based tracking)")
            
        self.video_processor.start_live_capture()
        
        if self.tracker:
            self.tracker.reset()

        try:
            frame_count = 0
            frames_processed = 0
            null_frame_count = 0
            last_log_frame = 0
            
            while True:
                # Get next frame
                frame = self.video_processor.get_frame(timeout=1.0)

                if frame is None:
                    null_frame_count += 1
                    if null_frame_count % 10 == 0:
                        print(f"[DEBUG] Waiting for frames... ({null_frame_count} timeouts)")
                    continue
                
                null_frame_count = 0  # Reset on successful frame

                # Process only every N frames
                if frame_count % self.process_every_n_frames != 0:
                    frame_count += 1
                    continue

                frames_processed += 1
                
                # Log progress every 10 processed frames
                if frames_processed % 10 == 1:
                    print(f"[CHECKPOINT] Processing frame {frame_count} (processed: {frames_processed})")
                    print(f"  Frame shape: {frame.shape}")

                # Preprocess frame
                preprocessed = self.frame_processor.preprocess_frame(frame)
                enhanced = self.frame_processor.enhance_frame(preprocessed)
                
                if frames_processed % 10 == 1:
                    print(f"  Preprocessed shape: {preprocessed.shape}, Enhanced shape: {enhanced.shape}")

                # Detect potholes
                print(f"[DETECT] Running SAM3 on frame {frame_count}...", end=" ", flush=True)
                # Enable verbose logging for first 3 processed frames
                verbose_mode = frames_processed <= 3
                potholes = self.sam_detector.detect_potholes(
                    enhanced,
                    confidence_threshold=self.confidence_threshold,
                    verbose=verbose_mode
                )
                print(f"Found {len(potholes)} raw detections")
                
                # Log detection details
                if potholes:
                    for i, p in enumerate(potholes):
                        conf = p.get('confidence', 0)
                        bbox = p.get('bbox', [])
                        print(f"  [DETECTION {i+1}] conf={conf:.3f}, bbox={bbox}")
                
                # Track raw detections
                self.total_raw_detections += len(potholes)

                # Apply deduplication if enabled
                frame_detections = []
                
                if self.enable_deduplication and self.tracker:
                    # Only get NEW unique potholes
                    unique_potholes = self.tracker.update(potholes, frame_count)
                    
                    for pothole in unique_potholes:
                        detection = self._create_detection(
                            frame_num=frame_count,
                            pothole=pothole
                        )
                        frame_detections.append(detection)
                        self.detections.append(detection)
                else:
                    # No deduplication
                    for pothole in potholes:
                        detection = self._create_detection(
                            frame_num=frame_count,
                            pothole=pothole
                        )
                        frame_detections.append(detection)
                        self.detections.append(detection)

                # Call callback function if provided (only for NEW detections)
                if callback_func and frame_detections:
                    callback_func(frame_detections, enhanced)

                # Save frame if requested
                if output_dir and len(potholes) > 0:
                    annotated = self.frame_processor.annotate_detections(
                        enhanced, potholes
                    )
                    self.frame_processor.save_annotated_frame(
                        annotated, output_dir, frame_count
                    )

                frame_count += 1

        except KeyboardInterrupt:
            print("\nStopping live processing...")
        finally:
            self.video_processor.stop_live_capture()
            print(f"\n[SUMMARY] Live processing complete:")
            print(f"  Total frames received: {frame_count}")
            print(f"  Frames actually processed: {frames_processed}")
            print(f"  Process every N frames: {self.process_every_n_frames}")
            if self.enable_deduplication:
                print(f"  Raw detections: {self.total_raw_detections}")
                print(f"  Unique potholes: {len(self.detections)}")
            else:
                print(f"  Total detections: {len(self.detections)}")

    def _create_detection(
        self,
        frame_num: int,
        pothole: Dict
    ) -> PotholeDetection:
        """
        Create detection result object

        Args:
            frame_num: Frame number
            pothole: Pothole detection dictionary

        Returns:
            PotholeDetection object
        """
        self.detection_counter += 1

        detection = PotholeDetection(
            detection_id=f"pothole_{self.detection_counter:06d}",
            frame_number=frame_num,
            timestamp=datetime.now().timestamp(),
            confidence=pothole['confidence'],
            bbox=pothole['bbox'],
            area=pothole['area']
        )

        return detection

    def get_detections_summary(self) -> Dict:
        """
        Get summary of all detections

        Returns:
            Summary dictionary
        """
        if not self.detections:
            return {
                'unique_potholes': 0,
                'total_raw_detections': self.total_raw_detections,
                'frames_with_potholes': 0,
                'average_confidence': 0.0,
                'deduplication_enabled': self.enable_deduplication
            }

        frames_with_potholes = len(set(d.frame_number for d in self.detections))
        avg_confidence = np.mean([d.confidence for d in self.detections])
        
        # Calculate deduplication ratio
        dedup_ratio = self.total_raw_detections / max(len(self.detections), 1)

        return {
            'unique_potholes': len(self.detections),
            'total_raw_detections': self.total_raw_detections,
            'deduplication_ratio': float(dedup_ratio),
            'deduplication_enabled': self.enable_deduplication,
            'frames_with_potholes': frames_with_potholes,
            'average_confidence': float(avg_confidence),
            'confidence_distribution': {
                'high (>0.8)': len([d for d in self.detections if d.confidence > 0.8]),
                'medium (0.5-0.8)': len([d for d in self.detections if 0.5 <= d.confidence <= 0.8]),
                'low (<0.5)': len([d for d in self.detections if d.confidence < 0.5])
            }
        }

    def export_results(self, output_file: str, format: str = 'json'):
        """
        Export detection results to file

        Args:
            output_file: Output file path
            format: Export format ('json' or 'csv')
        """
        from pathlib import Path

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            data = {
                'summary': self.get_detections_summary(),
                'detections': [d.to_dict() for d in self.detections]
            }

            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)

        elif format == 'csv':
            import csv

            if not self.detections:
                return

            fieldnames = ['detection_id', 'frame_number', 'timestamp', 'confidence',
                         'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'area']

            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for detection in self.detections:
                    row = {
                        'detection_id': detection.detection_id,
                        'frame_number': detection.frame_number,
                        'timestamp': detection.timestamp,
                        'confidence': detection.confidence,
                        'bbox_x': detection.bbox[0],
                        'bbox_y': detection.bbox[1],
                        'bbox_w': detection.bbox[2],
                        'bbox_h': detection.bbox[3],
                        'area': detection.area
                    }
                    writer.writerow(row)

        print(f"Exported {len(self.detections)} unique detections to {output_file}")
