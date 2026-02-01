"""
Telemetry Data Handler for Drone Footage
Processes and stores GPS, altitude, and other drone metadata
Supports extraction from DJI MP4 files via embedded subtitles
"""

import json
import re
import subprocess
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import csv
from pathlib import Path


@dataclass
class TelemetryData:
    """Telemetry data from drone"""
    timestamp: float
    frame_number: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None  # meters
    heading: Optional[float] = None  # degrees
    speed: Optional[float] = None  # m/s
    battery_level: Optional[float] = None  # percentage
    gimbal_pitch: Optional[float] = None  # degrees
    gimbal_yaw: Optional[float] = None  # degrees
    gimbal_roll: Optional[float] = None  # degrees

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> 'TelemetryData':
        """Create from dictionary"""
        return cls(**data)


class TelemetryHandler:
    """Handle telemetry data from drone video"""

    def __init__(self, telemetry_file: Optional[str] = None):
        """
        Initialize telemetry handler

        Args:
            telemetry_file: Path to telemetry data file (SRT, CSV, or JSON)
        """
        self.telemetry_file = telemetry_file
        self.telemetry_data: Dict[int, TelemetryData] = {}
        self.current_index = 0

        if telemetry_file:
            self.load_telemetry_file(telemetry_file)

    def load_telemetry_file(self, filepath: str) -> bool:
        """
        Load telemetry data from file

        Args:
            filepath: Path to telemetry file

        Returns:
            True if successful, False otherwise
        """
        file_path = Path(filepath)

        if not file_path.exists():
            print(f"Telemetry file not found: {filepath}")
            return False

        try:
            if file_path.suffix.lower() == '.srt':
                return self._load_srt_file(filepath)
            elif file_path.suffix.lower() == '.csv':
                return self._load_csv_file(filepath)
            elif file_path.suffix.lower() == '.json':
                return self._load_json_file(filepath)
            else:
                print(f"Unsupported telemetry file format: {file_path.suffix}")
                return False

        except Exception as e:
            print(f"Error loading telemetry file: {e}")
            return False

    def _load_srt_file(self, filepath: str) -> bool:
        """
        Load telemetry from SRT subtitle file (common DJI drone format)

        Args:
            filepath: Path to SRT file

        Returns:
            True if successful
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse SRT format
        entries = content.strip().split('\n\n')

        for entry in entries:
            lines = entry.strip().split('\n')
            if len(lines) < 3:
                continue

            frame_num = int(lines[0])
            # Skip timestamp line (lines[1])
            metadata_text = '\n'.join(lines[2:])

            # Parse metadata (example DJI SRT format)
            telemetry = self._parse_dji_metadata(metadata_text, frame_num)
            if telemetry:
                self.telemetry_data[frame_num] = telemetry

        print(f"Loaded {len(self.telemetry_data)} telemetry entries from SRT")
        return True

    def _parse_dji_metadata(self, text: str, frame_num: int) -> Optional[TelemetryData]:
        """
        Parse DJI metadata text from SRT subtitle

        Args:
            text: Metadata text string
            frame_num: Frame number (1-indexed from SRT, represents seconds)

        Returns:
            TelemetryData object or None
        """
        data = {
            'frame_number': frame_num,
            'timestamp': float(frame_num)  # Use frame_num as timestamp in seconds
        }

        # DJI Air 3S format examples:
        # [latitude: 12.345678] [longitude: 78.901234] [rel_alt: 50.000 abs_alt: 100.000]
        # Or: GPS(12.3456, 78.9012, 100) D:1.2m H:0.5m/s V:0.0m/s
        
        # Try newer DJI format first (Air 3S style)
        lat_match = re.search(r'\[latitude:\s*([-\d.]+)\]', text)
        lon_match = re.search(r'\[longitude:\s*([-\d.]+)\]', text)
        rel_alt_match = re.search(r'\[rel_alt:\s*([-\d.]+)', text)
        abs_alt_match = re.search(r'abs_alt:\s*([-\d.]+)', text)
        
        if lat_match and lon_match:
            data['latitude'] = float(lat_match.group(1))
            data['longitude'] = float(lon_match.group(1))
            if rel_alt_match:
                data['altitude'] = float(rel_alt_match.group(1))
            elif abs_alt_match:
                data['altitude'] = float(abs_alt_match.group(1))
        else:
            # Try older GPS format
            gps_match = re.search(r'GPS\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)', text)
            if gps_match:
                data['latitude'] = float(gps_match.group(1))
                data['longitude'] = float(gps_match.group(2))
                data['altitude'] = float(gps_match.group(3))

        # Extract speed/velocity info
        h_vel_match = re.search(r'H:\s*([-\d.]+)', text)
        v_vel_match = re.search(r'V:\s*([-\d.]+)', text)
        if h_vel_match:
            data['speed'] = float(h_vel_match.group(1))

        # Extract gimbal info if present
        gb_yaw_match = re.search(r'\[gb_yaw:\s*([-\d.]+)', text)
        gb_pitch_match = re.search(r'gb_pitch:\s*([-\d.]+)', text)
        gb_roll_match = re.search(r'gb_roll:\s*([-\d.]+)', text)
        
        if gb_yaw_match:
            data['gimbal_yaw'] = float(gb_yaw_match.group(1))
        if gb_pitch_match:
            data['gimbal_pitch'] = float(gb_pitch_match.group(1))
        if gb_roll_match:
            data['gimbal_roll'] = float(gb_roll_match.group(1))

        return TelemetryData(**data)

    def load_from_mp4(self, video_path: str, fps: float = 30.0) -> bool:
        """
        Extract telemetry from DJI MP4 video file using ffmpeg.
        DJI drones embed telemetry as subtitle streams in the video.

        Args:
            video_path: Path to MP4 video file
            fps: Video frame rate (for mapping seconds to frames)

        Returns:
            True if successful, False otherwise
        """
        video_file = Path(video_path)
        if not video_file.exists():
            print(f"Video file not found: {video_path}")
            return False

        try:
            # First, check if video has subtitle stream
            probe_result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 's', 
                 '-show_entries', 'stream=index,codec_name', 
                 '-of', 'json', str(video_path)],
                capture_output=True,
                text=True
            )
            
            if probe_result.returncode != 0:
                print(f"ffprobe error: {probe_result.stderr}")
                return False
                
            probe_data = json.loads(probe_result.stdout)
            if not probe_data.get('streams'):
                print("No subtitle stream found in video")
                return False
                
            print(f"Found subtitle stream in video, extracting telemetry...")
            
            # Extract subtitle stream as SRT
            result = subprocess.run(
                ['ffmpeg', '-y', '-i', str(video_path),
                 '-map', '0:s:0', '-f', 'srt', '-'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"ffmpeg extraction error: {result.stderr}")
                return False
                
            srt_content = result.stdout
            if not srt_content.strip():
                print("Extracted subtitle stream is empty")
                return False
                
            # Parse the SRT content
            return self._parse_srt_content(srt_content, fps)
            
        except FileNotFoundError:
            print("ffmpeg/ffprobe not found. Please install ffmpeg.")
            return False
        except Exception as e:
            print(f"Error extracting telemetry from MP4: {e}")
            return False

    def _parse_srt_content(self, srt_content: str, fps: float = 30.0) -> bool:
        """
        Parse SRT subtitle content to extract telemetry.

        Args:
            srt_content: Raw SRT subtitle text
            fps: Video frame rate

        Returns:
            True if successful
        """
        entries = srt_content.strip().split('\n\n')
        parsed_count = 0
        
        for entry in entries:
            lines = entry.strip().split('\n')
            if len(lines) < 3:
                continue

            try:
                subtitle_num = int(lines[0])
                # Parse timestamp: "00:00:00,000 --> 00:00:01,000"
                time_line = lines[1]
                time_match = re.match(r'(\d+):(\d+):(\d+),(\d+)', time_line)
                
                if time_match:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2))
                    seconds = int(time_match.group(3))
                    millis = int(time_match.group(4))
                    
                    total_seconds = hours * 3600 + minutes * 60 + seconds + millis / 1000
                    # Convert to frame number (approximate)
                    frame_num = int(total_seconds * fps)
                else:
                    frame_num = subtitle_num
                
                # Join remaining lines as metadata
                metadata_text = '\n'.join(lines[2:])
                
                # Parse metadata
                telemetry = self._parse_dji_metadata(metadata_text, frame_num)
                if telemetry and (telemetry.latitude is not None or telemetry.longitude is not None):
                    self.telemetry_data[frame_num] = telemetry
                    parsed_count += 1
                    
            except (ValueError, IndexError) as e:
                continue

        print(f"Extracted {parsed_count} telemetry entries from video (fps={fps})")
        return parsed_count > 0

    def get_telemetry_for_frame(self, frame_number: int, fps: float = 30.0) -> Optional[TelemetryData]:
        """
        Get telemetry for a specific video frame.
        Since DJI telemetry is typically 1Hz, this maps frame numbers to seconds.

        Args:
            frame_number: Video frame number
            fps: Video frame rate

        Returns:
            TelemetryData or None
        """
        # Try exact match first
        if frame_number in self.telemetry_data:
            return self.telemetry_data[frame_number]
        
        # Find closest telemetry sample
        if not self.telemetry_data:
            return None
            
        # Find the nearest available telemetry data
        closest_frame = min(self.telemetry_data.keys(), 
                          key=lambda x: abs(x - frame_number))
        
        # If within 2 seconds worth of frames, use it
        if abs(closest_frame - frame_number) < fps * 2:
            return self.telemetry_data[closest_frame]
            
        return None

    def _load_csv_file(self, filepath: str) -> bool:
        """
        Load telemetry from CSV file

        Args:
            filepath: Path to CSV file

        Returns:
            True if successful
        """
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                frame_num = int(row.get('frame_number', 0))

                telemetry = TelemetryData(
                    timestamp=float(row.get('timestamp', 0)),
                    frame_number=frame_num,
                    latitude=float(row['latitude']) if row.get('latitude') else None,
                    longitude=float(row['longitude']) if row.get('longitude') else None,
                    altitude=float(row['altitude']) if row.get('altitude') else None,
                    heading=float(row['heading']) if row.get('heading') else None,
                    speed=float(row['speed']) if row.get('speed') else None,
                    battery_level=float(row['battery_level']) if row.get('battery_level') else None,
                    gimbal_pitch=float(row['gimbal_pitch']) if row.get('gimbal_pitch') else None,
                    gimbal_yaw=float(row['gimbal_yaw']) if row.get('gimbal_yaw') else None,
                    gimbal_roll=float(row['gimbal_roll']) if row.get('gimbal_roll') else None
                )

                self.telemetry_data[frame_num] = telemetry

        print(f"Loaded {len(self.telemetry_data)} telemetry entries from CSV")
        return True

    def _load_json_file(self, filepath: str) -> bool:
        """
        Load telemetry from JSON file

        Args:
            filepath: Path to JSON file

        Returns:
            True if successful
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        if isinstance(data, list):
            for entry in data:
                frame_num = entry['frame_number']
                telemetry = TelemetryData.from_dict(entry)
                self.telemetry_data[frame_num] = telemetry
        elif isinstance(data, dict):
            for frame_num_str, entry in data.items():
                frame_num = int(frame_num_str)
                telemetry = TelemetryData.from_dict(entry)
                self.telemetry_data[frame_num] = telemetry

        print(f"Loaded {len(self.telemetry_data)} telemetry entries from JSON")
        return True

    def get_telemetry(self, frame_number: int) -> Optional[TelemetryData]:
        """
        Get telemetry data for specific frame

        Args:
            frame_number: Frame number

        Returns:
            TelemetryData or None if not found
        """
        return self.telemetry_data.get(frame_number)

    def add_telemetry(self, telemetry: TelemetryData):
        """
        Add telemetry data entry

        Args:
            telemetry: TelemetryData object
        """
        self.telemetry_data[telemetry.frame_number] = telemetry

    def interpolate_telemetry(self, frame_number: int) -> Optional[TelemetryData]:
        """
        Interpolate telemetry data if exact frame not available

        Args:
            frame_number: Frame number

        Returns:
            Interpolated TelemetryData or None
        """
        # If exact match exists, return it
        if frame_number in self.telemetry_data:
            return self.telemetry_data[frame_number]

        # Find nearest frames with telemetry
        frame_nums = sorted(self.telemetry_data.keys())

        if not frame_nums:
            return None

        # Find closest frame
        closest = min(frame_nums, key=lambda x: abs(x - frame_number))

        # If within reasonable range, use closest
        if abs(closest - frame_number) < 30:  # 1 second at 30fps
            return self.telemetry_data[closest]

        return None

    def export_telemetry(self, output_file: str, format: str = 'json'):
        """
        Export telemetry data to file

        Args:
            output_file: Output file path
            format: Export format ('json' or 'csv')
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            data = [t.to_dict() for t in self.telemetry_data.values()]
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)

        elif format == 'csv':
            if not self.telemetry_data:
                return

            fieldnames = list(next(iter(self.telemetry_data.values())).to_dict().keys())

            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for telemetry in self.telemetry_data.values():
                    writer.writerow(telemetry.to_dict())

        print(f"Exported telemetry to {output_file}")
