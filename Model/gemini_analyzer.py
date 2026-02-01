"""
Gemini-Powered Ticket Analyzer

Analyzes road/infrastructure images using Google Gemini Vision API
and generates comprehensive ticket data including:
- Issue type and severity
- Time-to-fix estimates
- Safety and traffic impact
- Reverse geocoded location

Usage:
    from gemini_analyzer import GeminiTicketAnalyzer
    
    analyzer = GeminiTicketAnalyzer(api_key="your-gemini-api-key")
    ticket_data = analyzer.analyze_frame(frame, lat=41.8262, lng=-71.4035)
"""

import os
import json
import base64
import requests
import cv2
import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

# Gemini API configuration - try different models if rate limited
GEMINI_MODELS = [
    "gemini-2.0-flash-lite-001",  # Lite version may have higher quota
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Reverse geocoding API (free, no key required)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


@dataclass
class TicketAnalysis:
    """Structured ticket analysis data from Gemini."""
    # Detection info
    issue_type: str
    severity: str  # low, medium, high
    confidence: float  # 0-100
    description: str
    
    # Location info (from reverse geocoding)
    street_name: Optional[str] = None
    nearest_intersection: Optional[str] = None
    district: Optional[str] = None
    
    # Effort estimate
    effort_minutes: Optional[int] = None
    
    # Risk assessment
    safety_risk: Optional[str] = None  # low, medium, high
    traffic_disruption: Optional[str] = None  # low, medium, high
    
    # Crew and priority
    crew_type: Optional[str] = None  # asphalt, electrical, signage, sanitation, other
    priority: Optional[int] = None  # 1-5
    impact_score: Optional[int] = None  # 1-100
    
    # Additional insights
    additional_observations: Optional[str] = None
    road_class: Optional[str] = None  # local, collector, arterial, highway
    surface_type: Optional[str] = None  # road, sidewalk, median, shoulder, other


class GeminiTicketAnalyzer:
    """Analyzes infrastructure issues using Gemini Vision API."""
    
    def __init__(self, api_key: str = None):
        """Initialize with Gemini API key."""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key required. Set GEMINI_API_KEY env var or pass api_key parameter.")
        
        print(f"[GeminiAnalyzer] Initialized with API key: {self.api_key[:10]}...")
    
    def _encode_image(self, frame: np.ndarray) -> str:
        """Encode OpenCV frame to base64 JPEG."""
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError("Failed to encode frame to JPEG")
        return base64.b64encode(buffer).decode('utf-8')
    
    def _reverse_geocode(self, lat: float, lng: float) -> Dict[str, str]:
        """Reverse geocode lat/lng to get street address info, detecting intersections."""
        import time
        
        # Check center and nearby points to detect intersections
        offsets = [
            (0, 0),           # center
            (0.0001, 0),      # north (~11m)
            (-0.0001, 0),     # south
            (0, 0.0001),      # east
            (0, -0.0001),     # west
        ]
        
        streets_found = set()
        first_result = None
        
        for dlat, dlng in offsets:
            result = self._nominatim_geocode(lat + dlat, lng + dlng, zoom=18)
            if result.get("street_name"):
                streets_found.add(result["street_name"])
                if first_result is None:
                    first_result = result
            time.sleep(0.3)  # Rate limit protection
        
        # Build intersection name if multiple streets found
        if len(streets_found) > 1:
            # Sort and join with &, abbreviate "Street" to "St"
            abbreviated = [s.replace(" Street", " St").replace(" Avenue", " Ave") for s in sorted(streets_found)]
            intersection_name = " & ".join(abbreviated[:2])  # Max 2 streets
            print(f"[GeminiAnalyzer] Detected intersection: {intersection_name}")
            if first_result:
                first_result["street_name"] = intersection_name
                return first_result
        
        # Single street or fallback
        if first_result and first_result.get("street_name"):
            return first_result
            
        # Fallback - return coordinates
        return {
            "street_name": f"{lat:.6f}, {lng:.6f}",
            "district": None,
            "full_address": f"Coordinates: {lat}, {lng}",
        }
    
    def _nominatim_geocode(self, lat: float, lng: float, zoom: int = 18) -> Dict[str, str]:
        """Call Nominatim API with specified zoom level for reverse geocoding."""
        try:
            response = requests.get(
                NOMINATIM_URL,
                params={
                    "lat": lat,
                    "lon": lng,
                    "format": "jsonv2",  # v2 format provides better structured data
                    "addressdetails": 1,
                    "zoom": zoom,  # 18 = building level, 16 = street level
                    "namedetails": 1,  # Include name details for better accuracy
                },
                headers={"User-Agent": "KaviPotholeDetector/1.0 (ravjeet@example.com)"},
                timeout=10,
            )
            
            if response.status_code == 200:
                data = response.json()
                address = data.get("address", {})
                
                print(f"[GeminiAnalyzer] Nominatim raw response (zoom={zoom}): {address}")
                
                # Extract street name with priority order (no house number)
                street_name = (
                    address.get("road") or
                    address.get("street") or
                    address.get("pedestrian") or
                    address.get("footway") or
                    address.get("path") or
                    address.get("cycleway") or
                    address.get("highway") or
                    address.get("residential") or
                    address.get("living_street") or
                    address.get("service") or
                    address.get("track") or
                    address.get("amenity") or
                    address.get("building") or
                    address.get("place")
                )
                
                # Get district/neighborhood with priority order (no quarter)
                district = (
                    address.get("neighbourhood") or 
                    address.get("suburb") or 
                    address.get("city_district") or
                    address.get("borough") or
                    address.get("town") or
                    address.get("village") or
                    address.get("city")
                )
                
                # Get city and state for context
                city = address.get("city") or address.get("town") or address.get("village") or address.get("municipality")
                state = address.get("state")
                
                # Build a more complete full address
                full_parts = [p for p in [street_name, district, city, state] if p]
                full_address = ", ".join(full_parts) if full_parts else data.get("display_name")
                
                print(f"[GeminiAnalyzer] Extracted street: {street_name}, district: {district}")
                
                return {
                    "street_name": street_name,
                    "district": district,
                    "city": city,
                    "state": state,
                    "full_address": full_address,
                }
                
        except requests.exceptions.Timeout:
            print(f"[GeminiAnalyzer] Nominatim timeout (zoom={zoom})")
        except Exception as e:
            print(f"[GeminiAnalyzer] Reverse geocoding failed: {e}")
        
        return {}
    
    def _call_gemini(self, image_base64: str, lat: float, lng: float, location_info: Dict) -> Dict[str, Any]:
        """Call Gemini Vision API to analyze the image."""
        
        # Build the analysis prompt
        prompt = f"""You are an expert infrastructure analyst for a city maintenance department. 
Analyze this road/infrastructure image and provide a detailed assessment.

Location: {location_info.get('full_address', f'Coordinates: {lat}, {lng}')}

Analyze the image and respond with a JSON object containing these fields:

{{
    "issue_type": "string - one of: pothole, crack, debris, flooding, damaged_sign, damaged_light, graffiti, fallen_tree, ice_hazard, utility_damage, sidewalk_damage, other",
    "severity": "string - one of: low, medium, high",
    "severity_reasoning": "string - brief explanation of severity assessment",
    "confidence": "number 0-100 - how confident you are in this assessment",
    "description": "string - detailed description of the issue",
    "effort_minutes": "number - estimated repair time in minutes",
    "safety_risk": "string - one of: low, medium, high",
    "traffic_disruption": "string - one of: low, medium, high",
    "crew_type": "string - one of: asphalt, electrical, signage, sanitation, landscaping, other",
    "priority": "number 1-5 - repair priority (1=urgent, 5=low)",
    "impact_score": "number 1-100 - overall impact on public safety and traffic",
    "road_class": "string - one of: local, collector, arterial, highway (estimate from surroundings)",
    "surface_type": "string - one of: road, sidewalk, median, shoulder, parking_lot, other",
    "additional_observations": "string - any other relevant observations about the image"
}}


Respond ONLY with the JSON object, no other text."""

        # Build the request
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 32,
                "topP": 0.95,
                "maxOutputTokens": 4096,
            }
        }
        
        # Call the API with retry logic and model fallback
        import time
        
        response = None
        for model in GEMINI_MODELS:
            api_url = f"{GEMINI_API_BASE}/{model}:generateContent"
            print(f"[GeminiAnalyzer] Trying model: {model}")
            
            for attempt in range(2):  # 2 retries per model
                response = requests.post(
                    f"{api_url}?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=60,
                )
                
                if response.status_code == 200:
                    print(f"[GeminiAnalyzer] Success with model: {model}")
                    break
                elif response.status_code == 429:
                    # Rate limited - try next model or wait
                    print(f"[GeminiAnalyzer] Rate limited on {model}, trying next...")
                    time.sleep(2)
                    break
                elif response.status_code == 404:
                    # Model not found - try next
                    print(f"[GeminiAnalyzer] Model {model} not found, trying next...")
                    break
                else:
                    print(f"[GeminiAnalyzer] Error {response.status_code} on {model}")
                    break
            
            if response and response.status_code == 200:
                break
        
        if response is None or response.status_code != 200:
            error_msg = response.text if response else "No response"
            print(f"[GeminiAnalyzer] All models failed. Last error: {error_msg}")
            raise Exception(f"Gemini API error: All models failed")
        
        # Parse the response
        result = response.json()
        
        # Extract the text content
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            # Clean up the JSON (remove markdown code blocks if present)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            return json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"[GeminiAnalyzer] Failed to parse response: {e}")
            print(f"[GeminiAnalyzer] Raw response: {result}")
            raise
    
    def analyze_frame(
        self, 
        frame: np.ndarray, 
        lat: float, 
        lng: float
    ) -> TicketAnalysis:
        """
        Analyze a frame and return structured ticket data.
        
        Args:
            frame: OpenCV image (BGR format)
            lat: Latitude coordinate
            lng: Longitude coordinate
            
        Returns:
            TicketAnalysis object with all analyzed data
        """
        print(f"[GeminiAnalyzer] Analyzing frame at ({lat}, {lng})...")
        
        # Step 1: Reverse geocode the location
        print("[GeminiAnalyzer] Reverse geocoding location...")
        location_info = self._reverse_geocode(lat, lng)
        print(f"[GeminiAnalyzer] Location: {location_info.get('street_name', 'Unknown')}")
        
        # Step 2: Encode the image
        print("[GeminiAnalyzer] Encoding image...")
        image_base64 = self._encode_image(frame)
        
        # Step 3: Call Gemini for analysis
        print("[GeminiAnalyzer] Calling Gemini Vision API...")
        analysis = self._call_gemini(image_base64, lat, lng, location_info)
        print(f"[GeminiAnalyzer] Analysis complete: {analysis.get('issue_type')} ({analysis.get('severity')})")
        
        # Step 4: Build the TicketAnalysis object
        return TicketAnalysis(
            issue_type=analysis.get("issue_type", "unknown"),
            severity=analysis.get("severity", "medium"),
            confidence=analysis.get("confidence", 50),
            description=analysis.get("description", ""),
            street_name=location_info.get("street_name") or analysis.get("street_name"),
            nearest_intersection=analysis.get("nearest_intersection"),
            district=location_info.get("district"),
            effort_minutes=analysis.get("effort_minutes"),
            safety_risk=analysis.get("safety_risk"),
            traffic_disruption=analysis.get("traffic_disruption"),
            crew_type=analysis.get("crew_type"),
            priority=analysis.get("priority"),
            impact_score=analysis.get("impact_score"),
            additional_observations=analysis.get("additional_observations"),
            road_class=analysis.get("road_class"),
            surface_type=analysis.get("surface_type"),
        )
    
    def analyze_file(self, image_path: str, lat: float, lng: float) -> TicketAnalysis:
        """Analyze an image file."""
        frame = cv2.imread(image_path)
        if frame is None:
            raise ValueError(f"Could not load image: {image_path}")
        return self.analyze_frame(frame, lat, lng)


def analyze_and_create_ticket(
    frame: np.ndarray,
    lat: float,
    lng: float,
    api_key: str = None,
) -> Dict[str, Any]:
    """
    Convenience function to analyze a frame and return ticket-ready data.
    
    Args:
        frame: OpenCV image (BGR)
        lat: Latitude
        lng: Longitude
        api_key: Gemini API key (optional, can use env var)
        
    Returns:
        Dictionary ready for database insertion
    """
    analyzer = GeminiTicketAnalyzer(api_key=api_key)
    analysis = analyzer.analyze_frame(frame, lat, lng)
    
    # Convert to dictionary for database
    data = asdict(analysis)
    
    # Rename issue_type to type for database compatibility
    data["type"] = data.pop("issue_type")
    
    return data


if __name__ == "__main__":
    import sys
    
    # Default API key (can be overridden)
    API_KEY = "AIzaSyAtvs6rDMw17b4Eodt6bUHlSMzzi2dw6IE"
    
    if len(sys.argv) < 2:
        print("Usage: python gemini_analyzer.py <image_path> [lat] [lng]")
        print("Example: python gemini_analyzer.py pothole.jpg 41.8262 -71.4035")
        sys.exit(1)
    
    image_path = sys.argv[1]
    lat = float(sys.argv[2]) if len(sys.argv) > 2 else 41.8262
    lng = float(sys.argv[3]) if len(sys.argv) > 3 else -71.4035
    
    print(f"\n{'='*60}")
    print(f"GEMINI TICKET ANALYZER")
    print(f"{'='*60}")
    print(f"Image: {image_path}")
    print(f"Location: ({lat}, {lng})")
    print(f"{'='*60}\n")
    
    analyzer = GeminiTicketAnalyzer(api_key=API_KEY)
    analysis = analyzer.analyze_file(image_path, lat, lng)
    
    print(f"\n{'='*60}")
    print(f"ANALYSIS RESULTS")
    print(f"{'='*60}")
    for key, value in asdict(analysis).items():
        if value is not None:
            print(f"  {key}: {value}")
    print(f"{'='*60}\n")

