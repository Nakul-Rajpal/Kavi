"""
Pothole Deduplication Module
Uses IoU (Intersection over Union) tracking to prevent counting the same pothole multiple times
across video frames.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np


@dataclass
class TrackedPothole:
    """Represents a unique pothole being tracked across frames"""
    pothole_id: int
    bbox: List[float]  # [x, y, w, h]
    first_frame: int
    last_frame: int
    confidence: float
    area: float
    detection_count: int = 1  # How many times this pothole was detected
    
    def update(self, bbox: List[float], frame_num: int, confidence: float, area: float):
        """Update tracked pothole with new detection"""
        self.bbox = bbox
        self.last_frame = frame_num
        self.confidence = max(self.confidence, confidence)  # Keep highest confidence
        self.area = area
        self.detection_count += 1


class PotholeTracker:
    """
    Tracks unique potholes across video frames using IoU + centroid distance matching.
    
    When a new detection comes in:
    1. Compute IoU with all active (recently seen) potholes
    2. Also compute centroid distance (for moving camera scenarios)
    3. If IoU > threshold OR centroid distance < threshold, it's the same pothole
    4. If no match, create a new unique pothole
    5. Return only NEW potholes (first sighting) for reporting
    """
    
    def __init__(
        self,
        iou_threshold: float = 0.15,
        centroid_threshold: float = 100.0,
        max_age_frames: int = 100,
        min_confidence: float = 0.5
    ):
        """
        Initialize the tracker.
        
        Args:
            iou_threshold: Minimum IoU to consider two detections the same pothole
            centroid_threshold: Maximum centroid distance (pixels) to consider same pothole
            max_age_frames: Frames since last detection before pothole is "forgotten"
            min_confidence: Minimum confidence to track a detection
        """
        self.iou_threshold = iou_threshold
        self.centroid_threshold = centroid_threshold
        self.max_age_frames = max_age_frames
        self.min_confidence = min_confidence
        
        self.tracked_potholes: List[TrackedPothole] = []
        self.pothole_counter = 0
        self.total_raw_detections = 0
    
    def update(
        self,
        detections: List[Dict],
        frame_num: int
    ) -> List[Dict]:
        """
        Process new detections and return only NEW unique potholes.
        
        Args:
            detections: List of detection dicts with 'bbox', 'confidence', 'area' keys
            frame_num: Current frame number
            
        Returns:
            List of detections that are NEW unique potholes (not seen before)
        """
        # Age out old potholes that haven't been seen recently
        self._age_out_stale_potholes(frame_num)
        
        new_unique_potholes = []
        
        for detection in detections:
            self.total_raw_detections += 1
            
            bbox = detection['bbox']
            confidence = detection['confidence']
            area = detection['area']
            
            # Skip low confidence detections
            if confidence < self.min_confidence:
                continue
            
            # Try to match with existing tracked potholes
            matched_pothole = self._find_matching_pothole(bbox)
            
            if matched_pothole is not None:
                # Update existing pothole
                matched_pothole.update(bbox, frame_num, confidence, area)
            else:
                # New unique pothole!
                self.pothole_counter += 1
                new_pothole = TrackedPothole(
                    pothole_id=self.pothole_counter,
                    bbox=bbox,
                    first_frame=frame_num,
                    last_frame=frame_num,
                    confidence=confidence,
                    area=area
                )
                self.tracked_potholes.append(new_pothole)
                
                # Add to list of new unique potholes to return
                new_unique_potholes.append(detection)
        
        return new_unique_potholes
    
    def _find_matching_pothole(self, bbox: List[float]) -> Optional[TrackedPothole]:
        """
        Find a tracked pothole that matches the given bounding box.
        Uses both IoU and centroid distance for matching (helpful with moving camera).
        
        Args:
            bbox: Bounding box [x, y, w, h]
            
        Returns:
            Matching TrackedPothole or None
        """
        best_match = None
        best_score = 0.0
        
        # Compute centroid of new detection
        new_centroid = self._get_centroid(bbox)
        
        for pothole in self.tracked_potholes:
            # Method 1: IoU matching
            iou = self._compute_iou(bbox, pothole.bbox)
            
            # Method 2: Centroid distance matching
            old_centroid = self._get_centroid(pothole.bbox)
            centroid_dist = self._compute_distance(new_centroid, old_centroid)
            
            # Match if EITHER IoU is high enough OR centroids are close enough
            iou_match = iou > self.iou_threshold
            centroid_match = centroid_dist < self.centroid_threshold
            
            if iou_match or centroid_match:
                # Score combines both metrics (higher is better match)
                # Normalize centroid distance to 0-1 range (inverse, so closer = higher)
                centroid_score = max(0, 1 - centroid_dist / self.centroid_threshold)
                combined_score = iou + centroid_score
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_match = pothole
        
        return best_match
    
    def _get_centroid(self, bbox: List[float]) -> Tuple[float, float]:
        """Get centroid (center point) of a bounding box [x, y, w, h]"""
        return (bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2)
    
    def _compute_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Compute Euclidean distance between two points"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def _compute_iou(self, box1: List[float], box2: List[float]) -> float:
        """
        Compute Intersection over Union (IoU) between two bounding boxes.
        
        Args:
            box1: First bbox [x, y, w, h]
            box2: Second bbox [x, y, w, h]
            
        Returns:
            IoU value between 0 and 1
        """
        # Convert [x, y, w, h] to [x1, y1, x2, y2]
        x1_1, y1_1 = box1[0], box1[1]
        x2_1, y2_1 = box1[0] + box1[2], box1[1] + box1[3]
        
        x1_2, y1_2 = box2[0], box2[1]
        x2_2, y2_2 = box2[0] + box2[2], box2[1] + box2[3]
        
        # Compute intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        # Check if there's an intersection
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Compute areas
        area1 = box1[2] * box1[3]
        area2 = box2[2] * box2[3]
        
        # Compute union
        union = area1 + area2 - intersection
        
        if union <= 0:
            return 0.0
        
        return intersection / union
    
    def _age_out_stale_potholes(self, current_frame: int):
        """
        Remove potholes that haven't been seen in max_age_frames.
        
        This prevents false matches when the drone returns to a similar area
        much later in the video.
        
        Args:
            current_frame: Current frame number
        """
        self.tracked_potholes = [
            p for p in self.tracked_potholes
            if (current_frame - p.last_frame) <= self.max_age_frames
        ]
    
    def get_statistics(self) -> Dict:
        """
        Get tracking statistics.
        
        Returns:
            Dictionary with tracking stats
        """
        return {
            'unique_potholes': self.pothole_counter,
            'total_raw_detections': self.total_raw_detections,
            'currently_tracking': len(self.tracked_potholes),
            'deduplication_ratio': (
                self.total_raw_detections / max(self.pothole_counter, 1)
            )
        }
    
    def get_all_unique_potholes(self) -> List[Dict]:
        """
        Get all tracked unique potholes with their statistics.
        
        Returns:
            List of pothole dictionaries
        """
        return [
            {
                'pothole_id': p.pothole_id,
                'bbox': p.bbox,
                'first_frame': p.first_frame,
                'last_frame': p.last_frame,
                'confidence': p.confidence,
                'area': p.area,
                'detection_count': p.detection_count
            }
            for p in self.tracked_potholes
        ]
    
    def reset(self):
        """Reset the tracker state"""
        self.tracked_potholes = []
        self.pothole_counter = 0
        self.total_raw_detections = 0
