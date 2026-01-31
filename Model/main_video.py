"""
Main entry point for SAM3 Video-based Pothole Detection
Uses native video tracking instead of frame-by-frame with deduplication
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime


def process_video_with_tracking(
    video_path: str,
    model_id: str = "facebook/sam3",
    output_dir: str = "./results_video",
    confidence: float = 0.5
):
    """
    Process video using SAM3's native video tracking.
    
    Args:
        video_path: Path to video file
        model_id: Hugging Face model ID
        output_dir: Output directory for results
        confidence: Confidence threshold
    """
    print("=" * 60)
    print("Kavi Pothole Detection - SAM3 Video Tracking Mode")
    print("=" * 60)
    print("\nThis mode uses SAM3's native video tracking to automatically")
    print("track potholes across frames - NO deduplication logic needed!")
    
    # Import here to avoid slow startup for help/version
    from .sam3_video_model import SAM3VideoModel, SAM3VideoPotholeDetector
    
    # Initialize model
    print("\n1. Loading SAM3 Video models...")
    sam_video = SAM3VideoModel(model_id=model_id)
    
    if not sam_video.load_models():
        print("Failed to load SAM3 models. Exiting.")
        return
        
    # Initialize detector
    detector = SAM3VideoPotholeDetector(sam_video)
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(output_dir) / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving results to: {session_dir}")
    
    # Process video
    print(f"\n2. Processing video: {video_path}")
    print(f"   Confidence threshold: {confidence}")
    
    results = detector.detect_potholes_in_video(
        video_path=video_path,
        confidence_threshold=confidence,
        output_dir=str(session_dir)
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("DETECTION SUMMARY")
    print("=" * 60)
    print(f"Video frames processed: {results['num_frames']}")
    print(f"Unique potholes found: {results['unique_potholes']}")
    
    if results['potholes']:
        print("\nDetected potholes:")
        for p in results['potholes']:
            print(f"  - {p['pothole_id']}: confidence={p['confidence']:.3f}, "
                  f"visible in frames {p['first_frame']}-{p['last_frame']} "
                  f"({p['frames_visible']} frames)")
    
    # Save results
    results_file = session_dir / "detections.json"
    
    # Remove non-serializable data for JSON export
    export_results = {
        'video_path': results['video_path'],
        'num_frames': results['num_frames'],
        'unique_potholes': results['unique_potholes'],
        'potholes': results['potholes'],
        'timestamp': timestamp
    }
    
    with open(results_file, 'w') as f:
        json.dump(export_results, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    print("=" * 60)
    print("\nProcessing complete!")
    
    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Kavi Pothole Detection - SAM3 Video Tracking Mode'
    )
    
    parser.add_argument(
        'video_path',
        type=str,
        help='Path to video file'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='facebook/sam3',
        help='Hugging Face model ID (default: facebook/sam3)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='./results_video',
        help='Output directory for results (default: ./results_video)'
    )
    
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.5,
        help='Confidence threshold for detection (default: 0.5)'
    )
    
    args = parser.parse_args()
    
    # Validate video exists
    if not Path(args.video_path).exists():
        print(f"Error: Video file not found: {args.video_path}")
        sys.exit(1)
    
    # Process video
    process_video_with_tracking(
        video_path=args.video_path,
        model_id=args.model,
        output_dir=args.output,
        confidence=args.confidence
    )


if __name__ == "__main__":
    main()
