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
        
        if move_range and len(move_range) >= 2:
            self.move_range = [min(move_range[0], move_range[1]), max(move_range[0], move_range[1])]
        else:
            self.move_range = move_range
            
        self.initial_position = initial_position
        self.current_position = float(initial_position)
        self.is_edge_reflect = is_edge_reflect
        self.dimmer_time = dimmer_time
        self.dimmer_time_ratio = dimmer_time_ratio
        self.time = 0.0
        
        self.direction = 1 if move_speed >= 0 else -1
        
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
        elif param_name == 'move_range':
            if value and len(value) >= 2:
                self.move_range = [min(value[0], value[1]), max(value[0], value[1])]
                
                if self.current_position < self.move_range[0]:
                    self.current_position = self.move_range[0]
                elif self.current_position > self.move_range[1]:
                    self.current_position = self.move_range[1]
            else:
                setattr(self, param_name, value)
        elif param_name == 'move_speed':
            old_direction = self.direction
            self.move_speed = value
            self.direction = 1 if value >= 0 else -1
            
            if old_direction != self.direction:
                import logging
                logger = logging.getLogger("color_signal_system")
                logger.info(f"Segment {self.segment_ID} direction changed: {old_direction} → {self.direction}")
        else:
            setattr(self, param_name, value)
    
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
        new_position = self.current_position + delta
        
        total_length = sum(self.length)
        
        if self.is_edge_reflect:
            if new_position < self.move_range[0]:
                new_position = self.move_range[0]
                self.direction = 1 
                self.move_speed = abs(self.move_speed)  
                
            elif new_position + total_length - 1 > self.move_range[1]:
                new_position = self.move_range[1] - total_length + 1
                self.direction = -1
                self.move_speed = -abs(self.move_speed)
        else:
            range_width = self.move_range[1] - self.move_range[0] + 1
            if new_position < self.move_range[0]:
                overshoot = self.move_range[0] - new_position
                new_position = self.move_range[1] - overshoot + 1
            elif new_position + total_length - 1 > self.move_range[1]:
                overshoot = new_position + total_length - 1 - self.move_range[1]
                new_position = self.move_range[0] + overshoot - 1
                
            if new_position < self.move_range[0]:
                new_position = self.move_range[0]
            elif new_position + total_length - 1 > self.move_range[1]:
                new_position = self.move_range[1] - total_length + 1
                
        self.current_position = new_position

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
                import logging
                logger = logging.getLogger("color_signal_system")
                logger.error(f"Error getting color {color_idx} from palette: {e}")
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
        
        ratio = getattr(self, 'dimmer_time_ratio', 1.0)
        cycle_time = int(self.dimmer_time[4] * ratio)
        
        if cycle_time <= 0:
            return 1.0
            
        current_time = int((self.time * 1000) % cycle_time)
        
        fade_in_start = int(self.dimmer_time[0] * ratio)
        fade_in_end = int(self.dimmer_time[1] * ratio)
        fade_out_start = int(self.dimmer_time[2] * ratio)
        fade_out_end = int(self.dimmer_time[3] * ratio)

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

    def get_light_data(self, palette: List[List[int]]) -> Dict[int, tuple[List[int], float]]:
        """
        Calculate the light data (color and transparency) for each LED covered by this segment.

        Args:
            palette: The current color palette (list of RGB colors) being used by the effect.

        Returns:
            A dictionary mapping LED index to a tuple of (RGB color, transparency).
        """
        light_data = {}
        brightness = self.apply_dimming()

        segment_colors = self.color[:4]
        while len(segment_colors) < 4:
            segment_colors.append(segment_colors[-1] if segment_colors else 0)
            
        segment_transparencies = self.transparency[:4]
        while len(segment_transparencies) < 4:
            segment_transparencies.append(segment_transparencies[-1] if segment_transparencies else 1.0)

        segment_lengths = self.length[:3]
        while len(segment_lengths) < 3:
            segment_lengths.append(segment_lengths[-1] if segment_lengths else 0)
        
        total_segment_length = sum(segment_lengths)
        if total_segment_length <= 0:
            return {}

        base_rgb = []
        for idx in segment_colors:
            if 0 <= idx < len(palette):
                base_rgb.append(palette[idx])
            else:
                base_rgb.append([255, 0, 0])

        start_led = math.floor(self.current_position)
        end_led = math.floor(self.current_position + total_segment_length - 1e-9)

        for led_idx in range(start_led, end_led + 1):
            relative_pos = led_idx - self.current_position
            
            relative_pos = max(0, min(relative_pos, total_segment_length - 1e-9))

            interpolated_color = [0, 0, 0]
            interpolated_transparency = 1.0
            
            if relative_pos < segment_lengths[0]:
                c1, c2 = base_rgb[0], base_rgb[1]
                tr1, tr2 = segment_transparencies[0], segment_transparencies[1]
                t = relative_pos / segment_lengths[0] if segment_lengths[0] > 0 else 0
            elif relative_pos < segment_lengths[0] + segment_lengths[1]:
                c1, c2 = base_rgb[1], base_rgb[2]
                tr1, tr2 = segment_transparencies[1], segment_transparencies[2]
                t = (relative_pos - segment_lengths[0]) / segment_lengths[1] if segment_lengths[1] > 0 else 0
            else:
                c1, c2 = base_rgb[2], base_rgb[3]
                tr1, tr2 = segment_transparencies[2], segment_transparencies[3]
                t = (relative_pos - segment_lengths[0] - segment_lengths[1]) / segment_lengths[2] if segment_lengths[2] > 0 else 0

            t = max(0.0, min(1.0, t))

            interpolated_color = interpolate_colors(c1, c2, t)
            interpolated_transparency = tr1 + (tr2 - tr1) * t
            
            final_color = apply_brightness(interpolated_color, brightness)
            
            light_data[led_idx] = (final_color, interpolated_transparency)
            
        return light_data

    def to_dict(self):
        segments_dict = {}
        for segment_id, segment in self.segments.items():
            if hasattr(segment, 'to_dict') and callable(segment.to_dict):
                segments_dict[str(segment_id)] = segment.to_dict()
            else:
                segments_dict[str(segment_id)] = {
                    "segment_ID": segment.segment_ID,
                    "color": segment.color,
                    "transparency": segment.transparency,
                    "length": segment.length,
                    "move_speed": segment.move_speed,
                    "move_range": segment.move_range,
                    "initial_position": segment.initial_position,
                    "current_position": segment.current_position,
                    "is_edge_reflect": segment.is_edge_reflect,
                    "dimmer_time": segment.dimmer_time,
                    "dimmer_time_ratio": getattr(segment, 'dimmer_time_ratio', 1.0),
                    "gradient": getattr(segment, 'gradient', False),
                    "fade": getattr(segment, 'fade', False),
                    "gradient_colors": getattr(segment, 'gradient_colors', [0, -1, -1])
                }
            
        return {
            "effect_ID": self.effect_ID,
            "led_count": self.led_count,
            "fps": self.fps,
            "time": self.time,
            "current_palette": self.current_palette,
            "segments": segments_dict
        }

    @classmethod
    def from_dict(cls, data):
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