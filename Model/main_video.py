"""
Main entry point for SAM3 Video-based Pothole Detection
Uses native video tracking instead of frame-by-frame with deduplication
Outputs CSV with telemetry data and saves frame images
"""

import argparse
import sys
import json
import csv
from pathlib import Path
from datetime import datetime


def process_video_with_tracking(
    video_path: str,
    model_id: str = "facebook/sam3",
    output_dir: str = "./results_video",
    confidence: float = 0.5,
    max_frames: int = 300,
    frame_skip: int = 5
):
    """
    Process video using SAM3's native video tracking.
    
    Args:
        video_path: Path to video file
        model_id: Hugging Face model ID
        output_dir: Output directory for results
        confidence: Confidence threshold
        max_frames: Maximum frames to process (memory limit)
        frame_skip: Process every Nth frame
    """
    print("=" * 60)
    print("Kavi Pothole Detection - SAM3 Video Tracking Mode")
    print("=" * 60)
    print("\nThis mode uses SAM3's native video tracking to automatically")
    print("track potholes across frames - NO deduplication logic needed!")
    print(f"\nMemory optimization: max {max_frames} frames, skip every {frame_skip}")
    
    # Import here to avoid slow startup for help/version
    from .sam3_video_model import SAM3VideoModel, SAM3VideoPotholeDetector
    from .telemetry_handler import TelemetryHandler
    
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
        output_dir=str(session_dir),
        max_frames=max_frames,
        frame_skip=frame_skip
    )
    
    # Extract telemetry from video
    print("\n3. Extracting telemetry from video...")
    telemetry_handler = TelemetryHandler()
    fps = results.get('fps', 30.0)
    
    # Try to extract telemetry from embedded subtitles in MP4
    telemetry_loaded = telemetry_handler.load_from_mp4(video_path, fps=fps)
    
    if not telemetry_loaded:
        # Try to find external SRT file
        video_file = Path(video_path)
        srt_path = video_file.with_suffix('.SRT')
        if not srt_path.exists():
            srt_path = video_file.with_suffix('.srt')
        
        if srt_path.exists():
            print(f"   Found external SRT file: {srt_path}")
            telemetry_handler.load_telemetry_file(str(srt_path))
        else:
            print("   No telemetry data found (no embedded subtitles or SRT file)")
    
    telemetry_count = len(telemetry_handler.telemetry_data)
    print(f"   Telemetry entries available: {telemetry_count}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("DETECTION SUMMARY")
    print("=" * 60)
    print(f"Video frames processed: {results['num_frames']}")
    print(f"Unique potholes found: {results['unique_potholes']}")
    print(f"Telemetry points: {telemetry_count}")
    
    if results['potholes']:
        print("\nDetected potholes:")
        for p in results['potholes']:
            print(f"  - {p['pothole_id']}: confidence={p['confidence']:.3f}, "
                  f"visible in frames {p['first_frame']}-{p['last_frame']} "
                  f"({p['frames_visible']} frames)")
            if p.get('image_filename'):
                print(f"    Image: {p['image_filename']}")
    
    # Save CSV with telemetry data
    csv_file = session_dir / "detections.csv"
    csv_fieldnames = [
        'pothole_id', 'confidence', 'frame_number', 'original_frame_number',
        'frames_visible', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h',
        'latitude', 'longitude', 'altitude', 'speed',
        'image_filename'
    ]
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        
        for p in results['potholes']:
            # Get telemetry for this detection's frame
            original_frame = p.get('original_frame_number', p['first_frame'])
            telemetry = telemetry_handler.get_telemetry_for_frame(original_frame, fps=fps)
            
            bbox = p.get('initial_bbox', [0, 0, 0, 0])
            
            row = {
                'pothole_id': p['pothole_id'],
                'confidence': round(p['confidence'], 4),
                'frame_number': p['first_frame'],
                'original_frame_number': original_frame,
                'frames_visible': p['frames_visible'],
                'bbox_x': round(bbox[0], 2) if bbox else 0,
                'bbox_y': round(bbox[1], 2) if bbox else 0,
                'bbox_w': round(bbox[2], 2) if bbox else 0,
                'bbox_h': round(bbox[3], 2) if bbox else 0,
                'latitude': telemetry.latitude if telemetry else None,
                'longitude': telemetry.longitude if telemetry else None,
                'altitude': telemetry.altitude if telemetry else None,
                'speed': telemetry.speed if telemetry else None,
                'image_filename': p.get('image_filename', '')
            }
            writer.writerow(row)
    
    print(f"\nCSV saved to: {csv_file}")
    
    # Save JSON results as well
    results_file = session_dir / "detections.json"
    
    # Remove non-serializable data for JSON export
    export_results = {
        'video_path': results['video_path'],
        'num_frames': results['num_frames'],
        'unique_potholes': results['unique_potholes'],
        'fps': fps,
        'potholes': results['potholes'],
        'telemetry_count': telemetry_count,
        'timestamp': timestamp
    }
    
    with open(results_file, 'w') as f:
        json.dump(export_results, f, indent=2)
    
    print(f"JSON saved to: {results_file}")
    print("=" * 60)
    print("\nProcessing complete!")
    print(f"\nOutput files in {session_dir}:")
    print(f"  - detections.csv (with GPS telemetry)")
    print(f"  - detections.json")
    print(f"  - frames/ (annotated detection images)")
    
    return results


def process_video_batch(
    video_paths: list,
    model_id: str = "facebook/sam3",
    output_dir: str = "./results_video",
    confidence: float = 0.5,
    max_frames: int = 300,
    frame_skip: int = 5
):
    """
    Process multiple videos with the model loaded ONCE.
    Much faster than processing videos individually.
    
    Args:
        video_paths: List of video file paths
        model_id: Hugging Face model ID
        output_dir: Output directory for results
        confidence: Confidence threshold
        max_frames: Maximum frames to process per video
        frame_skip: Process every Nth frame
    """
    from .sam3_video_model import SAM3VideoModel, SAM3VideoPotholeDetector
    from .telemetry_handler import TelemetryHandler
    
    print("=" * 60)
    print("Kavi Pothole Detection - BATCH MODE")
    print("=" * 60)
    print(f"\nProcessing {len(video_paths)} videos")
    print("Model will be loaded ONCE and reused for all videos")
    
    # Load model ONCE
    print("\n1. Loading SAM3 Video models (one-time)...")
    sam_video = SAM3VideoModel(model_id=model_id)
    
    if not sam_video.load_models():
        print("Failed to load SAM3 models. Exiting.")
        return []
    
    # Initialize detector (reuses the loaded model)
    detector = SAM3VideoPotholeDetector(sam_video)
    
    print("\n✓ Model loaded! Processing videos...\n")
    
    all_results = []
    
    for i, video_path in enumerate(video_paths):
        print(f"\n{'='*60}")
        print(f"VIDEO {i+1}/{len(video_paths)}: {Path(video_path).name}")
        print("=" * 60)
        
        # Create output directory for this video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = Path(video_path).stem
        session_dir = Path(output_dir) / f"{video_name}_{timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Process video (model already loaded - fast!)
        results = detector.detect_potholes_in_video(
            video_path=video_path,
            confidence_threshold=confidence,
            output_dir=str(session_dir),
            max_frames=max_frames,
            frame_skip=frame_skip
        )
        
        # Extract telemetry
        telemetry_handler = TelemetryHandler()
        fps = results.get('fps', 30.0)
        telemetry_handler.load_from_mp4(video_path, fps=fps)
        telemetry_count = len(telemetry_handler.telemetry_data)
        
        # Save CSV
        csv_file = session_dir / "detections.csv"
        csv_fieldnames = [
            'pothole_id', 'confidence', 'frame_number', 'original_frame_number',
            'frames_visible', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h',
            'latitude', 'longitude', 'altitude', 'speed',
            'image_filename'
        ]
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
            writer.writeheader()
            
            for p in results['potholes']:
                original_frame = p.get('original_frame_number', p['first_frame'])
                telemetry = telemetry_handler.get_telemetry_for_frame(original_frame, fps=fps)
                bbox = p.get('initial_bbox', [0, 0, 0, 0])
                
                row = {
                    'pothole_id': p['pothole_id'],
                    'confidence': round(p['confidence'], 4),
                    'frame_number': p['first_frame'],
                    'original_frame_number': original_frame,
                    'frames_visible': p['frames_visible'],
                    'bbox_x': round(bbox[0], 2) if bbox else 0,
                    'bbox_y': round(bbox[1], 2) if bbox else 0,
                    'bbox_w': round(bbox[2], 2) if bbox else 0,
                    'bbox_h': round(bbox[3], 2) if bbox else 0,
                    'latitude': telemetry.latitude if telemetry else None,
                    'longitude': telemetry.longitude if telemetry else None,
                    'altitude': telemetry.altitude if telemetry else None,
                    'speed': telemetry.speed if telemetry else None,
                    'image_filename': p.get('image_filename', '')
                }
                writer.writerow(row)
        
        # Save JSON
        results_file = session_dir / "detections.json"
        export_results = {
            'video_path': results['video_path'],
            'num_frames': results['num_frames'],
            'unique_potholes': results['unique_potholes'],
            'fps': fps,
            'potholes': results['potholes'],
            'telemetry_count': telemetry_count,
            'timestamp': timestamp
        }
        
        with open(results_file, 'w') as f:
            json.dump(export_results, f, indent=2)
        
        print(f"\n✓ Video {i+1} complete: {results['unique_potholes']} potholes found")
        print(f"  Results saved to: {session_dir}")
        
        all_results.append({
            'video': video_path,
            'potholes': results['unique_potholes'],
            'output_dir': str(session_dir)
        })
    
    # Final summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 60)
    total_potholes = sum(r['potholes'] for r in all_results)
    print(f"Videos processed: {len(all_results)}")
    print(f"Total potholes found: {total_potholes}")
    
    return all_results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Kavi Pothole Detection - SAM3 Video Tracking Mode'
    )
    
    parser.add_argument(
        'video_path',
        type=str,
        nargs='?',  # Make optional for batch mode
        help='Path to video file (or use --folder for batch processing)'
    )
    
    parser.add_argument(
        '--folder',
        type=str,
        help='Process ALL videos in this folder (batch mode - loads model once)'
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
    
    parser.add_argument(
        '--max-frames',
        type=int,
        default=300,
        help='Maximum frames to process for memory efficiency (default: 300)'
    )
    
    parser.add_argument(
        '--frame-skip',
        type=int,
        default=5,
        help='Process every Nth frame (default: 5)'
    )
    
    args = parser.parse_args()
    
    # Batch mode: process all videos in a folder
    if args.folder:
        folder = Path(args.folder)
        if not folder.exists():
            print(f"Error: Folder not found: {args.folder}")
            sys.exit(1)
        
        # Find all video files
        video_extensions = ['.mp4', '.MP4', '.mov', '.MOV', '.avi', '.AVI', '.mkv', '.MKV']
        video_paths = []
        for ext in video_extensions:
            video_paths.extend(folder.glob(f'*{ext}'))
        
        if not video_paths:
            print(f"Error: No video files found in {args.folder}")
            sys.exit(1)
        
        print(f"Found {len(video_paths)} videos in {args.folder}")
        
        # Process all videos with model loaded once
        process_video_batch(
            video_paths=[str(p) for p in sorted(video_paths)],
            model_id=args.model,
            output_dir=args.output,
            confidence=args.confidence,
            max_frames=args.max_frames,
            frame_skip=args.frame_skip
        )
    
    # Single video mode
    elif args.video_path:
        if not Path(args.video_path).exists():
            print(f"Error: Video file not found: {args.video_path}")
            sys.exit(1)
        
        process_video_with_tracking(
            video_path=args.video_path,
            model_id=args.model,
            output_dir=args.output,
            confidence=args.confidence,
            max_frames=args.max_frames,
            frame_skip=args.frame_skip
        )
    
    else:
        print("Error: Provide either a video path or --folder for batch processing")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
