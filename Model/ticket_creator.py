"""
Ticket Creator - Analyzes frames with Gemini and creates tickets in Supabase.

Complete pipeline:
1. SAM3 detects an issue in a frame
2. Gemini Vision analyzes the frame for detailed ticket data
3. Image is uploaded to Supabase Storage
4. Ticket is created in the database with all analyzed data

Usage:
    from ticket_creator import SmartTicketCreator
    
    creator = SmartTicketCreator(
        gemini_api_key="your-gemini-key",
    )
    
    # After SAM3 detects an issue:
    ticket = creator.create_smart_ticket(
        frame=cv2_image,  # numpy array (BGR)
        lat=41.8262,
        lng=-71.4035,
    )
"""

import os
import uuid
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import asdict

from supabase import create_client, Client
from gemini_analyzer import GeminiTicketAnalyzer, TicketAnalysis

# Supabase configuration
SUPABASE_URL = "https://iofndonrjbuubyjlgilt.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvZm5kb25yamJ1dWJ5amxnaWx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk4NjQ4OTYsImV4cCI6MjA4NTQ0MDg5Nn0._q9oE9ge2C1EDK5LTky4ySPvZHyQTqT243VddtbBEik"

# Default Gemini API key
DEFAULT_GEMINI_KEY = "AIzaSyAtvs6rDMw17b4Eodt6bUHlSMzzi2dw6IE"

STORAGE_BUCKET = "frames"


class SmartTicketCreator:
    """Creates tickets with Gemini-powered analysis."""
    
    def __init__(
        self, 
        gemini_api_key: str = None,
        supabase_url: str = None, 
        supabase_key: str = None
    ):
        """Initialize with API credentials."""
        # Supabase client
        self.supabase_url = supabase_url or SUPABASE_URL
        self.supabase_key = supabase_key or SUPABASE_ANON_KEY
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Gemini analyzer
        self.gemini_key = gemini_api_key or DEFAULT_GEMINI_KEY
        self.analyzer = GeminiTicketAnalyzer(api_key=self.gemini_key)
        
        print(f"[SmartTicketCreator] Initialized")
        print(f"[SmartTicketCreator] Supabase: {self.supabase_url}")
        print(f"[SmartTicketCreator] Gemini: Ready")

    def upload_frame(self, frame: np.ndarray, filename: str = None) -> str:
        """
        Upload a frame to Supabase Storage.
        
        Args:
            frame: OpenCV image (numpy array, BGR format)
            filename: Optional filename, auto-generated if not provided
            
        Returns:
            Public URL of the uploaded image
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"detection_{timestamp}_{unique_id}.jpg"
        
        # Encode frame to JPEG bytes
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError("Failed to encode frame to JPEG")
        
        image_bytes = buffer.tobytes()
        
        # Upload to Supabase Storage
        print(f"[SmartTicketCreator] Uploading frame: {filename} ({len(image_bytes)} bytes)")
        
        result = self.supabase.storage.from_(STORAGE_BUCKET).upload(
            path=filename,
            file=image_bytes,
            file_options={"content-type": "image/jpeg"}
        )
        
        # Get public URL
        public_url = self.supabase.storage.from_(STORAGE_BUCKET).get_public_url(filename)
        print(f"[SmartTicketCreator] Uploaded: {public_url}")
        
        return public_url

    def create_smart_ticket(
        self,
        frame: np.ndarray,
        lat: float,
        lng: float,
        sam3_confidence: float = None,
        filename: str = None,
    ) -> Dict[str, Any]:
        """
        Create a complete ticket with Gemini analysis.
        
        This is the main function to use. It:
        1. Analyzes the frame with Gemini Vision
        2. Reverse geocodes the location
        3. Uploads the frame to storage
        4. Creates the ticket in the database
        
        Args:
            frame: OpenCV image (numpy array, BGR format)
            lat: Latitude coordinate
            lng: Longitude coordinate
            sam3_confidence: Optional confidence score from SAM3 detection
            filename: Optional filename for the image
            
        Returns:
            Created ticket record from database
        """
        print(f"\n{'='*60}")
        print(f"[SmartTicketCreator] CREATING SMART TICKET")
        print(f"{'='*60}")
        print(f"Location: ({lat}, {lng})")
        
        # Step 1: Analyze with Gemini
        print(f"\n[Step 1/3] Analyzing frame with Gemini...")
        analysis = self.analyzer.analyze_frame(frame, lat, lng)
        print(f"  → Type: {analysis.issue_type}")
        print(f"  → Severity: {analysis.severity}")
        print(f"  → Confidence: {analysis.confidence}%")
        
        # Step 2: Upload the frame
        print(f"\n[Step 2/3] Uploading frame to storage...")
        image_url = self.upload_frame(frame, filename)
        print(f"  → URL: {image_url}")
        
        # Step 3: Create the database record
        print(f"\n[Step 3/3] Creating ticket in database...")
        
        # Build the record
        record = {
            "lat": lat,
            "lng": lng,
            "image_url": image_url,
            "type": analysis.issue_type,
            "severity": analysis.severity,
            "confidence": sam3_confidence or (analysis.confidence / 100),
            "street_name": analysis.street_name,
            "effort_minutes": analysis.effort_minutes,
            "status": "new",
        }
        
        # Remove None values
        record = {k: v for k, v in record.items() if v is not None}
        
        # Insert into database
        result = self.supabase.table("pings").insert(record).execute()
        
        if result.data:
            ticket = result.data[0]
            print(f"\n{'='*60}")
            print(f"[SmartTicketCreator] TICKET CREATED SUCCESSFULLY")
            print(f"{'='*60}")
            print(f"  ID: {ticket['id']}")
            print(f"  Type: {ticket.get('type')}")
            print(f"  Location: {ticket.get('street_name', f'({lat}, {lng})')}")
            print(f"  Severity: {ticket.get('severity')}")
            print(f"  Time to Fix: {ticket.get('effort_minutes', '?')} minutes")
            print(f"{'='*60}\n")
            return ticket
        else:
            raise Exception("Failed to create ticket")

    def create_smart_ticket_from_file(
        self,
        image_path: str,
        lat: float,
        lng: float,
        sam3_confidence: float = None,
    ) -> Dict[str, Any]:
        """
        Create a ticket from an image file path.
        
        Args:
            image_path: Path to the image file
            lat: Latitude coordinate
            lng: Longitude coordinate
            sam3_confidence: Optional confidence from SAM3
            
        Returns:
            Created ticket record
        """
        frame = cv2.imread(image_path)
        if frame is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        filename = os.path.basename(image_path)
        return self.create_smart_ticket(frame, lat, lng, sam3_confidence, filename)


# Legacy support - simple ticket creator without Gemini
class TicketCreator:
    """Simple ticket creator (for manual ticket data)."""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.supabase_url = supabase_url or SUPABASE_URL
        self.supabase_key = supabase_key or SUPABASE_ANON_KEY
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

    def upload_frame(self, frame: np.ndarray, filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"frame_{timestamp}_{unique_id}.jpg"
        
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError("Failed to encode frame to JPEG")
        
        image_bytes = buffer.tobytes()
        self.client.storage.from_(STORAGE_BUCKET).upload(
            path=filename,
            file=image_bytes,
            file_options={"content-type": "image/jpeg"}
        )
        
        return self.client.storage.from_(STORAGE_BUCKET).get_public_url(filename)

    def create_ticket(
        self,
        frame: np.ndarray,
        lat: float,
        lng: float,
        ticket_data: dict,
        filename: str = None
    ) -> dict:
        image_url = self.upload_frame(frame, filename)
        
        record = {
            "lat": lat,
            "lng": lng,
            "image_url": image_url,
            "type": ticket_data.get("type", "unknown"),
            "severity": ticket_data.get("severity"),
            "confidence": ticket_data.get("confidence"),
            "street_name": ticket_data.get("street_name"),
            "effort_minutes": ticket_data.get("effort_minutes"),
            "status": ticket_data.get("status", "new"),
        }
        
        record = {k: v for k, v in record.items() if v is not None}
        result = self.client.table("pings").insert(record).execute()
        
        if result.data:
            return result.data[0]
        raise Exception("Failed to create ticket")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ticket_creator.py <image_path> [lat] [lng]")
        print("Example: python ticket_creator.py pothole.jpg 41.8262 -71.4035")
        print("\nThis will:")
        print("  1. Analyze the image with Gemini Vision AI")
        print("  2. Reverse geocode the location")
        print("  3. Upload the image to Supabase Storage")
        print("  4. Create a ticket with all the analyzed data")
        sys.exit(1)
    
    image_path = sys.argv[1]
    lat = float(sys.argv[2]) if len(sys.argv) > 2 else 41.8262
    lng = float(sys.argv[3]) if len(sys.argv) > 3 else -71.4035
    
    creator = SmartTicketCreator()
    ticket = creator.create_smart_ticket_from_file(image_path, lat, lng)
    
    print("\nFinal ticket data:")
    for key, value in ticket.items():
        print(f"  {key}: {value}")
