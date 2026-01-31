"""
Example usage scripts for Kavi Pothole Detection System
Demonstrates various use cases and configurations
"""

import sys
from pathlib import Path

# Add Model to path
sys.path.insert(0, str(Path(__file__).parent))

from sam3_model import SAM3Model
from pothole_detector import PotholeDetectionPipeline
from results_reporter import ResultsReporter, LocalFileReporter, MultiReporter


def example_1_basic_video_processing():
    """Example 1: Basic video processing without telemetry"""
    print("=" * 60)
    print("Example 1: Basic Video Processing")
    print("=" * 60)

    # Paths (update these with your actual paths)
    VIDEO_PATH = "./sample_drone_video.mp4"
    CHECKPOINT_PATH = "./sam3_checkpoint.pt"
    OUTPUT_DIR = "./results/example1"

    # Initialize SAM3
    print("\nInitializing SAM3 model...")
    sam_model = SAM3Model(
        model_type="vit_h",
        checkpoint_path=CHECKPOINT_PATH,
        device="cuda"  # Use "cpu" if no GPU
    )

    if not sam_model.load_model():
        print("Failed to load model. Please check checkpoint path.")
        return

    # Create pipeline
    pipeline = PotholeDetectionPipeline(
        sam_model=sam_model,
        video_source=VIDEO_PATH,
        confidence_threshold=0.5,
        process_every_n_frames=5  # Process every 5th frame
    )

    # Process video
    print("\nProcessing video...")
    detections = pipeline.process_video(
        output_dir=OUTPUT_DIR,
        save_frames=True,  # Save annotated frames
        max_frames=100  # Process first 100 frames only (for demo)
    )

    # Print results
    print(f"\n✓ Found {len(detections)} potholes")
    print(f"✓ Results saved to {OUTPUT_DIR}")

    # Export results
    pipeline.export_results(f"{OUTPUT_DIR}/detections.json", format='json')
    pipeline.export_results(f"{OUTPUT_DIR}/detections.csv", format='csv')


def example_2_with_telemetry():
    """Example 2: Video processing with telemetry data"""
    print("=" * 60)
    print("Example 2: Video Processing with Telemetry")
    print("=" * 60)

    # Paths
    VIDEO_PATH = "./sample_drone_video.mp4"
    CHECKPOINT_PATH = "./sam3_checkpoint.pt"
    TELEMETRY_PATH = "./sample_telemetry.srt"  # Or .csv, .json
    OUTPUT_DIR = "./results/example2"

    # Initialize SAM3
    print("\nInitializing SAM3 model...")
    sam_model = SAM3Model(checkpoint_path=CHECKPOINT_PATH, device="cuda")
    sam_model.load_model()

    # Create pipeline with telemetry
    pipeline = PotholeDetectionPipeline(
        sam_model=sam_model,
        video_source=VIDEO_PATH,
        telemetry_file=TELEMETRY_PATH,  # Add telemetry
        confidence_threshold=0.6,
        process_every_n_frames=10
    )

    # Process video
    detections = pipeline.process_video(
        output_dir=OUTPUT_DIR,
        save_frames=True
    )

    # Show detections with GPS
    print("\nDetections with GPS coordinates:")
    for det in detections[:5]:  # Show first 5
        if det.telemetry:
            lat = det.telemetry.get('latitude', 'N/A')
            lon = det.telemetry.get('longitude', 'N/A')
            print(f"  {det.detection_id}: ({lat}, {lon}) - confidence: {det.confidence:.2f}")


def example_3_live_stream():
    """Example 3: Live stream processing"""
    print("=" * 60)
    print("Example 3: Live Stream Processing")
    print("=" * 60)

    CHECKPOINT_PATH = "./sam3_checkpoint.pt"
    OUTPUT_DIR = "./results/example3"

    # Initialize SAM3
    sam_model = SAM3Model(checkpoint_path=CHECKPOINT_PATH, device="cuda")
    sam_model.load_model()

    # Create pipeline for webcam (0) or RTSP stream
    pipeline = PotholeDetectionPipeline(
        sam_model=sam_model,
        video_source=0,  # Webcam, or use "rtsp://..." for drone stream
        confidence_threshold=0.6,
        process_every_n_frames=15  # Process every 15th frame for real-time
    )

    # Callback for detections
    def on_pothole_detected(detections, frame):
        """Called whenever potholes are detected"""
        for det in detections:
            print(f"🚨 POTHOLE DETECTED! Confidence: {det.confidence:.2f}, Area: {det.area:.0f}px")

    print("\nStarting live stream... Press Ctrl+C to stop")

    # Process live stream
    try:
        pipeline.process_live_stream(
            callback_func=on_pothole_detected,
            output_dir=OUTPUT_DIR
        )
    except KeyboardInterrupt:
        print("\n\nStopped by user")


def example_4_api_integration():
    """Example 4: Send results to API endpoint"""
    print("=" * 60)
    print("Example 4: API Integration")
    print("=" * 60)

    VIDEO_PATH = "./sample_drone_video.mp4"
    CHECKPOINT_PATH = "./sam3_checkpoint.pt"
    OUTPUT_DIR = "./results/example4"

    # API configuration
    API_ENDPOINT = "https://your-api.com/api/detections"
    API_KEY = "your_api_key_here"

    # Initialize SAM3
    sam_model = SAM3Model(checkpoint_path=CHECKPOINT_PATH, device="cuda")
    sam_model.load_model()

    # Create pipeline
    pipeline = PotholeDetectionPipeline(
        sam_model=sam_model,
        video_source=VIDEO_PATH,
        confidence_threshold=0.5,
        process_every_n_frames=5
    )

    # Set up multi-reporter
    reporter = MultiReporter()

    # Add API reporter
    api_reporter = ResultsReporter(
        api_endpoint=API_ENDPOINT,
        api_key=API_KEY,
        batch_size=10
    )
    api_reporter.start_background_reporting()
    reporter.add_reporter(api_reporter)

    # Add local file reporter as backup
    file_reporter = LocalFileReporter(OUTPUT_DIR)
    reporter.add_reporter(file_reporter)

    # Process video
    print("\nProcessing video and sending to API...")
    detections = pipeline.process_video(
        output_dir=OUTPUT_DIR,
        save_frames=True
    )

    # Report to API
    print(f"\nSending {len(detections)} detections to API...")
    reporter.report_detections(detections)
    reporter.flush()

    # Print statistics
    stats = api_reporter.get_statistics()
    print(f"\n✓ API Statistics:")
    print(f"  Sent: {stats['total_sent']}")
    print(f"  Failed: {stats['total_failed']}")

    # Cleanup
    reporter.stop()


def example_5_custom_configuration():
    """Example 5: Custom configuration and fine-tuning"""
    print("=" * 60)
    print("Example 5: Custom Configuration")
    print("=" * 60)

    from config import PipelineConfig, ModelConfig, VideoConfig, DetectionConfig

    VIDEO_PATH = "./sample_drone_video.mp4"
    CHECKPOINT_PATH = "./sam3_checkpoint.pt"
    OUTPUT_DIR = "./results/example5"

    # Create custom configuration
    config = PipelineConfig(
        model=ModelConfig(
            model_type="vit_h",
            checkpoint_path=CHECKPOINT_PATH,
            device="cuda"
        ),
        video=VideoConfig(
            resize_height=720,  # Process at 720p
            process_every_n_frames=3,  # Process every 3rd frame
            enable_enhancement=True,  # Enable image enhancement
            enable_denoising=False  # Disable denoising for speed
        ),
        detection=DetectionConfig(
            confidence_threshold=0.6,  # Higher confidence threshold
            min_pothole_area=200,  # Minimum size
            max_pothole_area=50000  # Maximum size
        )
    )

    print(f"\nConfiguration:")
    print(f"  Model: {config.model.model_type}")
    print(f"  Video: {config.video.resize_height}p, every {config.video.process_every_n_frames} frames")
    print(f"  Detection: threshold={config.detection.confidence_threshold}")

    # Initialize with config
    sam_model = SAM3Model(
        model_type=config.model.model_type,
        checkpoint_path=config.model.checkpoint_path,
        device=config.model.device
    )
    sam_model.load_model()

    pipeline = PotholeDetectionPipeline(
        sam_model=sam_model,
        video_source=VIDEO_PATH,
        confidence_threshold=config.detection.confidence_threshold,
        process_every_n_frames=config.video.process_every_n_frames
    )

    # Process
    detections = pipeline.process_video(output_dir=OUTPUT_DIR)

    # Summary
    summary = pipeline.get_detections_summary()
    print(f"\n✓ Summary:")
    print(f"  Total detections: {summary['total_detections']}")
    print(f"  Frames with potholes: {summary['frames_with_potholes']}")
    print(f"  Average confidence: {summary['average_confidence']:.3f}")


def example_6_batch_processing():
    """Example 6: Batch process multiple videos"""
    print("=" * 60)
    print("Example 6: Batch Processing Multiple Videos")
    print("=" * 60)

    CHECKPOINT_PATH = "./sam3_checkpoint.pt"
    VIDEO_DIR = "./videos"
    OUTPUT_BASE_DIR = "./results/batch"

    # List of videos to process
    video_files = [
        "drone_flight_1.mp4",
        "drone_flight_2.mp4",
        "drone_flight_3.mp4"
    ]

    # Initialize SAM3 once (reuse for all videos)
    print("\nInitializing SAM3 model...")
    sam_model = SAM3Model(checkpoint_path=CHECKPOINT_PATH, device="cuda")
    sam_model.load_model()

    all_detections = []

    # Process each video
    for i, video_file in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] Processing {video_file}...")

        video_path = Path(VIDEO_DIR) / video_file
        output_dir = Path(OUTPUT_BASE_DIR) / video_path.stem

        if not video_path.exists():
            print(f"  ⚠ Video not found, skipping...")
            continue

        # Create pipeline for this video
        pipeline = PotholeDetectionPipeline(
            sam_model=sam_model,  # Reuse model
            video_source=str(video_path),
            confidence_threshold=0.5,
            process_every_n_frames=10
        )

        # Process
        detections = pipeline.process_video(
            output_dir=str(output_dir),
            save_frames=True
        )

        all_detections.extend(detections)

        print(f"  ✓ Found {len(detections)} potholes")

    # Overall summary
    print(f"\n{'='*60}")
    print(f"Batch Processing Complete")
    print(f"{'='*60}")
    print(f"Total videos processed: {len(video_files)}")
    print(f"Total potholes detected: {len(all_detections)}")
    print(f"Average per video: {len(all_detections) / len(video_files):.1f}")


def main():
    """Run examples"""
    examples = {
        '1': ('Basic Video Processing', example_1_basic_video_processing),
        '2': ('With Telemetry Data', example_2_with_telemetry),
        '3': ('Live Stream', example_3_live_stream),
        '4': ('API Integration', example_4_api_integration),
        '5': ('Custom Configuration', example_5_custom_configuration),
        '6': ('Batch Processing', example_6_batch_processing),
    }

    print("\n" + "=" * 60)
    print("Kavi Pothole Detection - Example Usage")
    print("=" * 60)
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  q. Quit")

    choice = input("\nSelect example (1-6): ").strip()

    if choice in examples:
        _, func = examples[choice]
        print()
        func()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
