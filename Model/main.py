"""
Main entry point for Kavi Pothole Detection System
Example usage of the complete pipeline
"""

import argparse
import sys
from pathlib import Path

from .sam3_model import SAM3Model
from .pothole_detector import PotholeDetectionPipeline
from .results_reporter import ResultsReporter, LocalFileReporter, MultiReporter
from .config import PipelineConfig


def process_video_file(
    video_path: str,
    model_id: str = "facebook/sam3",
    telemetry_file: str = None,
    output_dir: str = "./results",
    api_endpoint: str = None,
    api_key: str = None,
    confidence: float = 0.5,
    process_every_n: int = 5
):
    """
    Process a video file for pothole detection

    Args:
        video_path: Path to video file
        model_id: Hugging Face model ID (e.g., facebook/sam3-large)
        telemetry_file: Path to telemetry data file
        output_dir: Output directory for results
        api_endpoint: API endpoint for results
        api_key: API authentication key
        confidence: Confidence threshold
        process_every_n: Process every Nth frame
    """
    print("=" * 60)
    print("Kavi Pothole Detection System with SAM3")
    print("=" * 60)

    # Initialize SAM3 model
    print("\n1. Loading SAM3 model...")
    sam_model = SAM3Model(
        model_id=model_id,
        device="cuda"
    )

    if not sam_model.load_model():
        print("Failed to load SAM3 model. Exiting.")
        return

    # Initialize detection pipeline
    print("\n2. Initializing detection pipeline...")
    pipeline = PotholeDetectionPipeline(
        sam_model=sam_model,
        video_source=video_path,
        telemetry_file=telemetry_file,
        confidence_threshold=confidence,
        process_every_n_frames=process_every_n
    )

    # Set up reporters
    print("\n3. Setting up results reporters...")
    multi_reporter = MultiReporter()

    # Add local file reporter
    file_reporter = LocalFileReporter(output_dir)
    multi_reporter.add_reporter(file_reporter)

    # Add API reporter if endpoint provided
    if api_endpoint:
        api_reporter = ResultsReporter(
            api_endpoint=api_endpoint,
            api_key=api_key,
            batch_size=10
        )
        api_reporter.start_background_reporting()
        multi_reporter.add_reporter(api_reporter)

    # Process video
    print("\n4. Processing video...")
    print(f"Video: {video_path}")
    print(f"Confidence threshold: {confidence}")
    print(f"Processing every {process_every_n} frame(s)")
    print()

    detections = pipeline.process_video(
        output_dir=output_dir,
        save_frames=True
    )

    # Report results
    print("\n5. Reporting results...")
    multi_reporter.report_detections(detections)
    multi_reporter.flush()

    # Save summary
    summary = pipeline.get_detections_summary()
    file_reporter.save_summary(summary)

    # Export results
    results_file = Path(output_dir) / file_reporter.session_dir.name / "detections.json"
    pipeline.export_results(str(results_file), format='json')

    csv_file = Path(output_dir) / file_reporter.session_dir.name / "detections.csv"
    pipeline.export_results(str(csv_file), format='csv')

    # Print summary
    print("\n" + "=" * 60)
    print("DETECTION SUMMARY")
    print("=" * 60)
    print(f"Total detections: {summary['total_detections']}")
    print(f"Frames with potholes: {summary['frames_with_potholes']}")
    print(f"Average confidence: {summary['average_confidence']:.3f}")
    print(f"Detections with GPS: {summary['detections_with_gps']}")
    print("\nConfidence distribution:")
    for level, count in summary['confidence_distribution'].items():
        print(f"  {level}: {count}")
    print("\nResults saved to:", file_reporter.session_dir)
    print("=" * 60)

    # Cleanup
    multi_reporter.stop()
    print("\nProcessing complete!")


def process_live_stream(
    video_source: str,
    model_id: str = "facebook/sam3",
    output_dir: str = "./results",
    api_endpoint: str = None,
    api_key: str = None,
    confidence: float = 0.5,
    process_every_n: int = 5
):
    """
    Process live video stream

    Args:
        video_source: Camera index or stream URL
        model_id: Hugging Face model ID (e.g., facebook/sam3-large)
        output_dir: Output directory for results
        api_endpoint: API endpoint for results
        api_key: API authentication key
        confidence: Confidence threshold
        process_every_n: Process every Nth frame
    """
    print("=" * 60)
    print("Kavi Pothole Detection System - Live Stream with SAM3")
    print("=" * 60)

    # Initialize SAM3 model
    print("\n1. Loading SAM3 model...")
    sam_model = SAM3Model(
        model_id=model_id,
        device="cuda"
    )

    if not sam_model.load_model():
        print("Failed to load SAM3 model. Exiting.")
        return

    # Initialize detection pipeline
    print("\n2. Initializing detection pipeline...")
    pipeline = PotholeDetectionPipeline(
        sam_model=sam_model,
        video_source=video_source,
        telemetry_file=None,  # No telemetry for live stream
        confidence_threshold=confidence,
        process_every_n_frames=process_every_n
    )

    # Set up reporters
    print("\n3. Setting up results reporters...")
    multi_reporter = MultiReporter()

    file_reporter = LocalFileReporter(output_dir)
    multi_reporter.add_reporter(file_reporter)

    if api_endpoint:
        api_reporter = ResultsReporter(
            api_endpoint=api_endpoint,
            api_key=api_key,
            batch_size=5  # Smaller batch for live stream
        )
        api_reporter.start_background_reporting()
        multi_reporter.add_reporter(api_reporter)

    # Callback function for detections
    def detection_callback(detections, frame):
        """Called when potholes are detected"""
        print(f"[DETECTION] Found {len(detections)} pothole(s) in frame")
        for det in detections:
            print(f"  - {det.detection_id}: confidence={det.confidence:.3f}, area={det.area:.0f}")

        # Report to UI
        multi_reporter.report_detections(detections)

    # Process live stream
    print("\n4. Processing live stream...")
    print("Press Ctrl+C to stop")
    print()

    try:
        pipeline.process_live_stream(
            callback_func=detection_callback,
            output_dir=output_dir
        )
    except KeyboardInterrupt:
        print("\n\nStopping...")

    # Cleanup
    multi_reporter.flush()
    summary = pipeline.get_detections_summary()
    file_reporter.save_summary(summary)

    # Print summary
    print("\n" + "=" * 60)
    print("DETECTION SUMMARY")
    print("=" * 60)
    print(f"Total detections: {summary['total_detections']}")
    print(f"Frames with potholes: {summary['frames_with_potholes']}")
    print(f"Average confidence: {summary['average_confidence']:.3f}")
    print("\nResults saved to:", file_reporter.session_dir)
    print("=" * 60)

    multi_reporter.stop()
    print("\nProcessing complete!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Kavi Pothole Detection System using SAM3'
    )

    parser.add_argument(
        'video_source',
        type=str,
        help='Video file path, camera index (e.g. 0), or live stream URL (rtsp://... or rtmp://... for DJI Air 3S etc.)'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='facebook/sam3',
        help='Hugging Face model ID (default: facebook/sam3)'
    )

    parser.add_argument(
        '--telemetry',
        type=str,
        default=None,
        help='Path to telemetry data file (SRT, CSV, or JSON)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='./results',
        help='Output directory for results (default: ./results)'
    )

    parser.add_argument(
        '--api-endpoint',
        type=str,
        default=None,
        help='API endpoint URL for sending results'
    )

    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='API authentication key'
    )

    parser.add_argument(
        '--confidence',
        type=float,
        default=0.5,
        help='Confidence threshold for detection (default: 0.5)'
    )

    parser.add_argument(
        '--process-every-n',
        type=int,
        default=5,
        help='Process every Nth frame (default: 5)'
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Process live video stream (camera index or RTSP/RTMP URL). See DJI_AIR_3S_SETUP.md for DJI drone setup.'
    )

    args = parser.parse_args()

    # Validate inputs: for file mode, source must exist; for live mode, allow URL or camera index
    if not args.live:
        if not Path(args.video_source).exists():
            print(f"Error: Video file not found: {args.video_source}")
            sys.exit(1)
    # For --live: video_source can be camera index ("0") or stream URL (rtsp://... or rtmp://...)

    # Run appropriate mode
    if args.live:
        process_live_stream(
            video_source=args.video_source,
            model_id=args.model,
            output_dir=args.output,
            api_endpoint=args.api_endpoint,
            api_key=args.api_key,
            confidence=args.confidence,
            process_every_n=args.process_every_n
        )
    else:
        process_video_file(
            video_path=args.video_source,
            model_id=args.model,
            telemetry_file=args.telemetry,
            output_dir=args.output,
            api_endpoint=args.api_endpoint,
            api_key=args.api_key,
            confidence=args.confidence,
            process_every_n=args.process_every_n
        )


if __name__ == "__main__":
    main()
