"""
Telemetry Data Handler for Drone Footage
Processes and stores GPS, altitude, and other drone metadata
"""

import json
from typing import Dict, Optional, List
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
        Parse DJI metadata text

        Args:
            text: Metadata text string
            frame_num: Frame number

        Returns:
            TelemetryData object or None
        """
        # Example DJI SRT format parsing
        # Format varies by drone model - this is a simplified parser
        data = {
            'frame_number': frame_num,
            'timestamp': datetime.now().timestamp()
        }

        # Extract GPS coordinates
        if 'GPS' in text:
            # Parse GPS data (latitude, longitude, altitude)
            # Format example: GPS (12.3456, 78.9012, 100)
            import re
            gps_match = re.search(r'GPS\s*\(([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\)', text)
            if gps_match:
                data['latitude'] = float(gps_match.group(1))
                data['longitude'] = float(gps_match.group(2))
                data['altitude'] = float(gps_match.group(3))

        return TelemetryData(**data)

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
