"""
Batch Upload Detections to Supabase

Processes detection results from SAM3 video analysis:
1. Reads detections.csv files from results_video/
2. Deduplicates frames (multiple potholes can share same frame)
3. Analyzes each unique frame with Gemini Vision
4. Uploads frames to Supabase Storage
5. Creates tickets in the pings table

CSV Format from SAM3:
pothole_id,confidence,frame_number,original_frame_number,frames_visible,
bbox_x,bbox_y,bbox_w,bbox_h,latitude,longitude,altitude,speed,image_filename

Note: If lat/long are empty in CSV, generates Providence, RI coordinates.

Usage:
    cd Model
    python batch_upload_detections.py
"""

import os
import sys
import csv
import random
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import cv2
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from supabase import create_client, Client
from gemini_analyzer import GeminiTicketAnalyzer

# Supabase configuration
SUPABASE_URL = "https://iofndonrjbuubyjlgilt.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvZm5kb25yamJ1dWJ5amxnaWx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk4NjQ4OTYsImV4cCI6MjA4NTQ0MDg5Nn0._q9oE9ge2C1EDK5LTky4ySPvZHyQTqT243VddtbBEik"

# Default Gemini API key
DEFAULT_GEMINI_KEY = "AIzaSyAtvs6rDMw17b4Eodt6bUHlSMzzi2dw6IE"

STORAGE_BUCKET = "frames"

# Providence, RI center coordinates
PROVIDENCE_LAT = 41.8240
PROVIDENCE_LNG = -71.4128

# Radius for random offset (in degrees, ~0.01 = ~1km)
OFFSET_RADIUS = 0.015  # ~1.5km radius


def generate_random_coordinates() -> Tuple[float, float]:
    """Generate random coordinates within Providence area."""
    lat_offset = random.uniform(-OFFSET_RADIUS, OFFSET_RADIUS)
    lng_offset = random.uniform(-OFFSET_RADIUS, OFFSET_RADIUS)
    return (
        PROVIDENCE_LAT + lat_offset,
        PROVIDENCE_LNG + lng_offset
    )


def load_detections_from_csv(results_dir: Path) -> List[Dict]:
    """
    Load all detections from detections.csv files.
    
    Returns list of detections with:
    - pothole_id, confidence, frame_number, original_frame_number
    - frames_visible, bbox (x,y,w,h)
    - latitude, longitude (if available)
    - image_path (full path to frame image)
    """
    all_detections = []
    
    for session_dir in sorted(results_dir.iterdir()):
        if not session_dir.is_dir():
            continue
            
        csv_file = session_dir / "detections.csv"
        if not csv_file.exists():
            continue
            
        frames_dir = session_dir / "frames"
        if not frames_dir.exists():
            print(f"  Warning: frames directory not found in {session_dir.name}")
            continue
            
        print(f"\nLoading from: {session_dir.name}")
        
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                image_filename = row.get("image_filename", "").strip()
                if not image_filename:
                    continue
                    
                image_path = frames_dir / image_filename
                if not image_path.exists():
                    print(f"  Warning: Image not found: {image_filename}")
                    continue
                
                # Parse lat/long if available
                lat = row.get("latitude", "").strip()
                lng = row.get("longitude", "").strip()
                
                detection = {
                    "session": session_dir.name,
                    "pothole_id": row["pothole_id"],
                    "confidence": float(row["confidence"]),
                    "frame_number": int(row["frame_number"]),
                    "original_frame_number": int(row["original_frame_number"]),
                    "frames_visible": int(row["frames_visible"]),
                    "bbox_x": float(row["bbox_x"]),
                    "bbox_y": float(row["bbox_y"]),
                    "bbox_w": float(row["bbox_w"]),
                    "bbox_h": float(row["bbox_h"]),
                    "latitude": float(lat) if lat else None,
                    "longitude": float(lng) if lng else None,
                    "altitude": float(row["altitude"]) if row.get("altitude", "").strip() else None,
                    "speed": float(row["speed"]) if row.get("speed", "").strip() else None,
                    "image_path": str(image_path),
                    "image_filename": image_filename,
                }
                
                all_detections.append(detection)
                print(f"  Loaded: {detection['pothole_id']} (conf: {detection['confidence']:.2f})")
    
    return all_detections


def deduplicate_detections(detections: List[Dict]) -> List[Dict]:
    """
    Deduplicate detections by unique frame.
    When multiple potholes are on the same frame, keep the one with highest confidence.
    """
    # Group by (session, original_frame_number)
    frame_groups: Dict[Tuple[str, int], List[Dict]] = {}
    
    for det in detections:
        key = (det["session"], det["original_frame_number"])
        if key not in frame_groups:
            frame_groups[key] = []
        frame_groups[key].append(det)
    
    # Keep the highest confidence detection per frame
    unique_detections = []
    for key, group in frame_groups.items():
        best = max(group, key=lambda x: x["confidence"])
        unique_detections.append(best)
        if len(group) > 1:
            print(f"  Frame {key}: kept {best['pothole_id']} (conf: {best['confidence']:.2f}), "
                  f"discarded {len(group)-1} others")
    
    # Sort by session and frame number
    unique_detections.sort(key=lambda x: (x["session"], x["original_frame_number"]))
    
    return unique_detections


def upload_frame_to_storage(supabase: Client, image_path: str, filename: str) -> str:
    """Upload frame to Supabase Storage and return public URL."""
    frame = cv2.imread(image_path)
    if frame is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    # Encode to JPEG
    success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise ValueError("Failed to encode frame to JPEG")
    
    image_bytes = buffer.tobytes()
    
    # Upload (handle if already exists)
    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(
            path=filename,
            file=image_bytes,
            file_options={"content-type": "image/jpeg"}
        )
    except Exception as e:
        error_str = str(e)
        if "Duplicate" in error_str or "already exists" in error_str.lower():
            print(f"  File already exists, using existing URL")
        else:
            print(f"  Upload warning: {e}")
    
    # Get public URL
    public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(filename)
    return public_url


def process_detections(
    detections: List[Dict],
    supabase: Client,
    analyzer: GeminiTicketAnalyzer,
    delay_between_calls: float = 3.0,
    skip_gemini: bool = False
) -> List[Dict]:
    """
    Process each detection:
    1. Use lat/long from CSV or generate Providence coordinates
    2. Analyze with Gemini (if not skipped)
    3. Upload to Storage
    4. Create ticket in database
    """
    created_tickets = []
    total = len(detections)
    
    for i, det in enumerate(detections):
        print(f"\n{'='*60}")
        print(f"Processing {i+1}/{total}: {det['pothole_id']} from {det['session']}")
        print(f"{'='*60}")
        
        # Use coordinates from CSV if available, otherwise generate
        if det["latitude"] and det["longitude"]:
            lat, lng = det["latitude"], det["longitude"]
            print(f"Using telemetry coordinates: ({lat:.6f}, {lng:.6f})")
        else:
            lat, lng = generate_random_coordinates()
            print(f"Generated coordinates: ({lat:.6f}, {lng:.6f})")
        
        # Load frame
        frame = cv2.imread(det["image_path"])
        if frame is None:
            print(f"  Error: Could not load image")
            continue
        
        # Analyze with Gemini (or use defaults)
        if skip_gemini:
            print(f"Skipping Gemini analysis (using defaults)...")
            severities = ['low', 'medium', 'high']
            analysis = type('obj', (object,), {
                'issue_type': 'pothole',
                'severity': random.choice(severities),
                'confidence': det['confidence'] * 100,
                'street_name': None,
                'effort_minutes': random.choice([30, 45, 60, 90, 120]),
            })()
        else:
            print(f"Analyzing with Gemini...")
            try:
                analysis = analyzer.analyze_frame(frame, lat, lng)
                print(f"  Type: {analysis.issue_type}")
                print(f"  Severity: {analysis.severity}")
                print(f"  Confidence: {analysis.confidence}%")
                print(f"  Street: {analysis.street_name}")
            except Exception as e:
                print(f"  Gemini error: {e}")
                # Use defaults
                severities = ['low', 'medium', 'high']
                analysis = type('obj', (object,), {
                    'issue_type': 'pothole',
                    'severity': random.choice(severities),
                    'confidence': det['confidence'] * 100,
                    'street_name': None,
                    'effort_minutes': random.choice([30, 45, 60, 90, 120]),
                })()
        
        # Upload frame to storage
        print(f"Uploading frame to storage...")
        storage_filename = f"{det['session']}_{det['image_filename']}"
        try:
            image_url = upload_frame_to_storage(supabase, det["image_path"], storage_filename)
            print(f"  URL: {image_url}")
        except Exception as e:
            print(f"  Upload error: {e}")
            continue
        
        # Create database record
        print(f"Creating ticket in database...")
        record = {
            "lat": lat,
            "lng": lng,
            "image_url": image_url,
            "type": analysis.issue_type,
            "severity": analysis.severity,
            "confidence": det["confidence"],  # Use SAM3 confidence (0-1)
            "street_name": getattr(analysis, 'street_name', None),
            "effort_minutes": getattr(analysis, 'effort_minutes', None),
            "status": "new",
        }
        
        # Remove None values
        record = {k: v for k, v in record.items() if v is not None}
        
        try:
            result = supabase.table("pings").insert(record).execute()
            if result.data:
                ticket = result.data[0]
                print(f"  Created ticket ID: {ticket['id']}")
                created_tickets.append(ticket)
            else:
                print(f"  Error: No data returned from insert")
        except Exception as e:
            print(f"  Database error: {e}")
        
        # Delay to avoid rate limits
        if i < total - 1 and not skip_gemini:
            print(f"Waiting {delay_between_calls}s before next...")
            time.sleep(delay_between_calls)
    
    return created_tickets


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch upload detections to Supabase")
    parser.add_argument("--skip-gemini", action="store_true", 
                       help="Skip Gemini analysis and use default values")
    parser.add_argument("--delay", type=float, default=3.0,
                       help="Delay between Gemini API calls (seconds)")
    args = parser.parse_args()
    
    print("="*60)
    print("BATCH UPLOAD DETECTIONS TO SUPABASE")
    print("="*60)
    
    # Find results directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    results_dir = project_root / "results_video"
    
    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        sys.exit(1)
    
    print(f"\nResults directory: {results_dir}")
    
    # Load all detections from CSV files
    print("\n1. Loading detections from CSV files...")
    all_detections = load_detections_from_csv(results_dir)
    print(f"\n   Total detections found: {len(all_detections)}")
    
    if not all_detections:
        print("No detections found. Exiting.")
        sys.exit(0)
    
    # Deduplicate by frame
    print("\n2. Deduplicating by frame...")
    unique_detections = deduplicate_detections(all_detections)
    print(f"\n   Unique frames to process: {len(unique_detections)}")
    print(f"   (Removed {len(all_detections) - len(unique_detections)} duplicates)")
    
    # Initialize clients
    print("\n3. Initializing Supabase and Gemini...")
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    
    if args.skip_gemini:
        print("   Gemini analysis will be SKIPPED")
        analyzer = None
    else:
        analyzer = GeminiTicketAnalyzer(api_key=DEFAULT_GEMINI_KEY)
    
    # Process detections
    print(f"\n4. Processing {len(unique_detections)} detections...")
    created_tickets = process_detections(
        unique_detections,
        supabase,
        analyzer,
        delay_between_calls=args.delay,
        skip_gemini=args.skip_gemini
    )
    
    # Summary
    print("\n" + "="*60)
    print("BATCH UPLOAD COMPLETE")
    print("="*60)
    print(f"Total detections processed: {len(unique_detections)}")
    print(f"Tickets created: {len(created_tickets)}")
    print("="*60)


if __name__ == "__main__":
    main()
