from typing import Dict, List, Any, Tuple, Optional
import json
import sys
sys.path.append('..')
from models.light_segment import LightSegment
from utils.color_utils import blend_colors, apply_transparency, apply_brightness

class LightEffect:
    """
    LightEffect manages multiple LightSegment instances to create a complete lighting effect.
    This class follows the specification for managing LED tape light segments.
    """
    
    def __init__(self, effect_ID: int, led_count: int, fps: int):
        """
        Initialize a LightEffect instance.
        
        Args:
            effect_ID: Unique identifier for this effect
            led_count: Total number of LEDs
            fps: Frame rate for animation updates
        """
        self.effect_ID = effect_ID
        self.segments: Dict[int, LightSegment] = {}
        self.led_count = led_count
        self.fps = fps
        self.time_step = 1.0 / fps
        self.time = 0.0
        self.current_palette = "A"
        
    def set_palette(self, palette_id: str):
        """
        Set the current palette for this effect.
        Updates all segments to use the new palette.
        
        Args:
            palette_id: ID of the palette to use
        """
        self.current_palette = palette_id
        

        for segment in self.segments.values():
            segment.rgb_color = segment.calculate_rgb(self.current_palette)
        
    def add_segment(self, segment_ID: int, segment: LightSegment):
        """
        Add a segment of light to the effect.
        
        Args:
            segment_ID: Unique identifier for the segment
            segment: LightSegment instance to add
        """
        self.segments[segment_ID] = segment
        
    def remove_segment(self, segment_ID: int):
        """
        Remove a segment from the effect.
        
        Args:
            segment_ID: ID of the segment to remove
        """
        if segment_ID in self.segments:
            del self.segments[segment_ID]
    
    def update_segment_param(self, segment_ID: int, param_name: str, value: Any):
        """
        Update a parameter of a specific LightSegment.
        
        Args:
            segment_ID: ID of the segment to update
            param_name: Name of the parameter to update
            value: New value for the parameter
        """
        if segment_ID in self.segments:
            self.segments[segment_ID].update_param(param_name, value)
    
    def update_all(self):
        """
        Update all segments based on the frame rate.
        Process movement and time-based effects for each frame.
        """
        self.time += self.time_step
        
        for segment in self.segments.values():
            segment.time = self.time
            segment.update_position(self.fps)
    
    def get_led_output(self) -> List[List[int]]:
        """
        Get the final color values for all LEDs, accounting for overlapping segments.
        
        Returns:
            List of RGB color values for each LED [r, g, b]
        """

        led_colors = [[0, 0, 0] for _ in range(self.led_count)]
        led_transparency = [1.0 for _ in range(self.led_count)]
        
        sorted_segments = sorted(self.segments.items(), key=lambda x: x[0])
        
        for segment_id, segment in sorted_segments:
            segment_data = segment.get_light_data(self.current_palette)
            
            if segment_data['brightness'] <= 0:
                continue
                
            positions = segment_data['positions']
            colors = segment_data['colors']
            transparency = segment_data['transparency']
            
            start_pos = max(0, int(positions[0]))
            end_pos = min(self.led_count - 1, int(positions[3]))
            
            for led_idx in range(start_pos, end_pos + 1):
                if led_idx < 0 or led_idx >= self.led_count:
                    continue

                if led_idx <= positions[1]:
                    rel_pos = (led_idx - positions[0]) / max(1, positions[1] - positions[0])
                    trans_idx = 0
                    color1 = colors[0]
                    color2 = colors[1]
                    
                elif led_idx <= positions[2]:
                    rel_pos = (led_idx - positions[1]) / max(1, positions[2] - positions[1])
                    trans_idx = 1
                    color1 = colors[1]
                    color2 = colors[2]
                    
                else:
                    rel_pos = (led_idx - positions[2]) / max(1, positions[3] - positions[2])
                    trans_idx = 2
                    color1 = colors[2]
                    color2 = colors[3]

                from utils.color_utils import interpolate_colors
                led_color = interpolate_colors(color1, color2, rel_pos)
                current_transparency = transparency[trans_idx]

                if led_colors[led_idx] == [0, 0, 0]:
                    led_colors[led_idx] = led_color
                    led_transparency[led_idx] = current_transparency
                else:
                    weight_current = led_transparency[led_idx]
                    weight_new = current_transparency * (1.0 - led_transparency[led_idx])
                    total_weight = weight_current + weight_new
                    
                    if total_weight > 0:
                        weight_current /= total_weight
                        weight_new /= total_weight

                        led_colors[led_idx] = blend_colors(
                            [led_colors[led_idx], led_color],
                            [weight_current, weight_new]
                        )

                    led_transparency[led_idx] = max(0.0, min(1.0, 
                        led_transparency[led_idx] + current_transparency * (1.0 - led_transparency[led_idx])
                    ))
        
        return led_colors
        
    def to_dict(self) -> Dict:
        """
        Convert the effect to a dictionary representation for serialization.
        
        Returns:
            Dictionary containing effect properties
        """
        segments_dict = {}
        for segment_id, segment in self.segments.items():
            segments_dict[str(segment_id)] = segment.to_dict()
            
        return {
            "effect_ID": self.effect_ID,
            "led_count": self.led_count,
            "fps": self.fps,
            "time": self.time,
            "current_palette": self.current_palette,
            "segments": segments_dict
        }
        
    @classmethod
    def from_dict(cls, data: Dict):
        """
        Create an effect from a dictionary representation (deserialization).
        
        Args:
            data: Dictionary containing effect properties
            
        Returns:
            A new LightEffect instance
        """
        effect = cls(
            effect_ID=data["effect_ID"],
            led_count=data["led_count"],
            fps=data["fps"]
        )
        
        if "time" in data:
            effect.time = data["time"]
            
        if "current_palette" in data:
            effect.current_palette = data["current_palette"]
            
        for segment_id_str, segment_data in data["segments"].items():
            segment = LightSegment.from_dict(segment_data)
            effect.add_segment(int(segment_id_str), segment)
            
        return effect
        
    def save_to_json(self, file_path: str):
        """
        Save the effect configuration to a JSON file.
        
        Args:
            file_path: Path to save the JSON file
        """
        data = self.to_dict()
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
            
    @classmethod
    def load_from_json(cls, file_path: str):
        """
        Load an effect configuration from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            A new LightEffect instance with the loaded configuration
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        return cls.from_dict(data)