from typing import List, Dict, Any, Optional
import math
import sys
sys.path.append('..')
from config import DEFAULT_COLOR_PALETTES
from utils.color_utils import interpolate_colors, apply_brightness

class LightSegment:
    """
    LightSegment represents a segment of light with specific properties like color, position, and movement.
    This class follows the specification from the LED tape light signal processing system.
    """

    def __init__(self, segment_ID: int, color: List[int], transparency: List[float], 
                length: List[int], move_speed: float, move_range: List[int], 
                initial_position: int, is_edge_reflect: bool, dimmer_time: List[int], 
                dimmer_time_ratio: float = 1.0):
        """
        Initialize a LightSegment instance.
        
        Args:
            segment_ID: Unique identifier for this segment
            color: List of color indices from the palette (4 elements: left to right)
            transparency: Transparency values for each color point (0.0~1.0)
            length: Lengths of each segment section (3 elements)
            move_speed: Speed of movement in LED particles per second (Positive: right, Negative: left)
            move_range: Range of movement [left_edge, right_edge]
            initial_position: Initial position of the segment
            is_edge_reflect: Whether to reflect at edges (True) or wrap around (False)
            dimmer_time: Fade timing parameters [fade_in_start, fade_in_end, fade_out_start, fade_out_end, cycle_length]
            dimmer_time_ratio: Ratio to stretch or shrink dimmer_time (default: 1.0)
        """
        self.segment_ID = segment_ID
        self.color = color
        self.transparency = transparency
        self.length = length
        self.move_speed = move_speed
        self.move_range = move_range
        self.initial_position = initial_position
        self.current_position = float(initial_position)
        self.is_edge_reflect = is_edge_reflect
        self.dimmer_time = dimmer_time
        self.dimmer_time_ratio = dimmer_time_ratio
        self.time = 0.0
        
        self.gradient = False
        self.fade = False
        self.gradient_colors = [0, -1, -1]

        self.rgb_color = self.calculate_rgb()
        self.total_length = sum(self.length)

    def update_param(self, param_name: str, value: Any):
        """
        Update a specific parameter of the segment.
        
        Args:
            param_name: Name of the parameter to update
            value: New value for the parameter
        """
        if param_name == 'color':
            setattr(self, param_name, value)
            self.rgb_color = self.calculate_rgb()
        elif param_name == 'gradient_colors':
            self.gradient_colors = value
            if self.gradient_colors[0] == 1:
                self.gradient = True
        elif param_name == 'gradient':
            self.gradient = value
            if self.gradient and self.gradient_colors[0] == 0:
                self.gradient_colors[0] = 1
        else:
            setattr(self, param_name, value)
            
        if param_name == 'move_range':
            if self.current_position < self.move_range[0]:
                self.current_position = self.move_range[0]
            elif self.current_position > self.move_range[1]:
                self.current_position = self.move_range[1]
    
    def update_position(self, fps: int):
        """
        Update the position of the segment based on move_speed and fps.
        Based on the move_speed, only specified LED particles are moved in 1 second.
        
        Args:
            fps: Frames per second
        """
        dt = 1.0 / fps
        self.time += dt
        
        delta = self.move_speed * dt
        self.current_position += delta
        
        if self.is_edge_reflect:
            if self.current_position < self.move_range[0]:
                self.current_position = 2 * self.move_range[0] - self.current_position
                self.move_speed *= -1
            elif self.current_position > self.move_range[1]:
                self.current_position = 2 * self.move_range[1] - self.current_position
                self.move_speed *= -1
        else:
            if self.current_position < self.move_range[0]:
                self.current_position = self.move_range[1] - (self.move_range[0] - self.current_position)
            elif self.current_position > self.move_range[1]:
                self.current_position = self.move_range[0] + (self.current_position - self.move_range[1])

    def calculate_rgb(self, palette_name: str = "A") -> List[List[int]]:
        """
        Calculate RGB color values from color palette indices.
        
        Args:
            palette_name: Name of the palette to use
            
        Returns:
            List of RGB values corresponding to each color index in format [[r0, g0, b0], ..., [r3, g3, b3]]
        """
        palette = DEFAULT_COLOR_PALETTES.get(palette_name, DEFAULT_COLOR_PALETTES["A"])
        
        rgb_values = []
        for i, color_idx in enumerate(self.color):
            try:
                if isinstance(color_idx, int) and 0 <= color_idx < len(palette):
                    rgb_values.append(palette[color_idx])
                else:
                    rgb_values.append([255, 0, 0])
            except Exception as e:
                print(f"Error getting color {color_idx} from palette: {e}")
                rgb_values.append([255, 0, 0])
        
        while len(rgb_values) < 4:
            if rgb_values:
                rgb_values.append(rgb_values[-1])
            else:
                rgb_values.append([255, 0, 0])
        
        return rgb_values

    def apply_dimming(self) -> float:
        """
        Apply fade effect based on dimmer_time parameters.
        Implements the fade in/out functionality as specified in the requirements.
        Uses dimmer_time_ratio to scale the timing values.
        
        Returns:
            Brightness level from 0.0 to 1.0
        """
        if not self.fade or not self.dimmer_time or len(self.dimmer_time) < 5 or self.dimmer_time[4] <= 0:
            return 1.0 
        
        cycle_time = int(self.dimmer_time[4] * self.dimmer_time_ratio)
        
        if cycle_time <= 0:
            return 1.0
            
        current_time = int((self.time * 1000) % cycle_time)
        
        fade_in_start = int(self.dimmer_time[0] * self.dimmer_time_ratio)
        fade_in_end = int(self.dimmer_time[1] * self.dimmer_time_ratio)
        fade_out_start = int(self.dimmer_time[2] * self.dimmer_time_ratio)
        fade_out_end = int(self.dimmer_time[3] * self.dimmer_time_ratio)

        if current_time < fade_in_start:
            return 0.0
        elif current_time < fade_in_end:
            progress = (current_time - fade_in_start) / max(1, fade_in_end - fade_in_start)
            return progress
        elif current_time < fade_out_start:
            return 1.0 
        elif current_time < fade_out_end:
            progress = (current_time - fade_out_start) / max(1, fade_out_end - fade_out_start)
            return 1.0 - progress 
        else:
            return 0.0

    def get_light_data(self, palette_name: str = "A") -> dict:
        """
        Get data for light rendering based on current segment state.
        Considers position, color, transparency, and applies gradients and fading if enabled.
        
        Args:
            palette_name: Name of the palette to use
            
        Returns:
            Dictionary with segment rendering information
        """
        brightness = self.apply_dimming() if self.fade else 1.0
        
        segment_start = int(self.current_position - self.total_length / 2)
        positions = [
            segment_start,                          
            segment_start + self.length[0],           
            segment_start + self.length[0] + self.length[1],  
            segment_start + self.total_length        
        ]

        if self.gradient and self.gradient_colors[0] == 1 and self.gradient_colors[1] >= 0 and self.gradient_colors[2] >= 0:
            palette = DEFAULT_COLOR_PALETTES.get(palette_name, DEFAULT_COLOR_PALETTES["A"])
            left_color = palette[self.gradient_colors[1]] if 0 <= self.gradient_colors[1] < len(palette) else [255, 0, 0]
            right_color = palette[self.gradient_colors[2]] if 0 <= self.gradient_colors[2] < len(palette) else [0, 0, 255]
            
            colors = [
                left_color,
                interpolate_colors(left_color, right_color, 0.33),
                interpolate_colors(left_color, right_color, 0.67),
                right_color
            ]
        else:
            colors = self.calculate_rgb(palette_name)
        
        if brightness < 1.0:
            colors = [apply_brightness(color, brightness) for color in colors]
        
        light_data = {
            'segment_id': self.segment_ID,
            'brightness': brightness,
            'positions': positions,
            'colors': colors,
            'transparency': self.transparency
        }
        
        return light_data
        
    def to_dict(self) -> Dict:
        """
        Convert the segment to a dictionary representation for serialization.
        
        Returns:
            Dictionary containing segment properties
        """
        data = {
            "segment_ID": self.segment_ID,
            "color": self.color,
            "transparency": self.transparency,
            "length": self.length,
            "move_speed": self.move_speed,
            "move_range": self.move_range,
            "initial_position": self.initial_position,
            "current_position": self.current_position,
            "is_edge_reflect": self.is_edge_reflect,
            "dimmer_time": self.dimmer_time,
            "dimmer_time_ratio": self.dimmer_time_ratio,
            "gradient": self.gradient,
            "fade": self.fade,
            "gradient_colors": self.gradient_colors
        }
            
        return data
        
    @classmethod
    def from_dict(cls, data: Dict):
        """
        Create a segment from a dictionary representation (deserialization).
        
        Args:
            data: Dictionary containing segment properties
            
        Returns:
            A new LightSegment instance
        """
        segment = cls(
            segment_ID=data["segment_ID"],
            color=data["color"],
            transparency=data["transparency"],
            length=data["length"],
            move_speed=data["move_speed"],
            move_range=data["move_range"],
            initial_position=data["initial_position"],
            is_edge_reflect=data["is_edge_reflect"],
            dimmer_time=data["dimmer_time"],
            dimmer_time_ratio=data.get("dimmer_time_ratio", 1.0) 
        )

        if "current_position" in data:
            segment.current_position = data["current_position"] 

        if "gradient" in data:
            segment.gradient = data["gradient"]
        if "fade" in data:
            segment.fade = data["fade"]
        if "gradient_colors" in data:
            segment.gradient_colors = data["gradient_colors"]
            
        return segment