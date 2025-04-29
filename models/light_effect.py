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
        import logging
        logger = logging.getLogger("color_signal_system")
        logger.info(f"Effect {self.effect_ID} setting palette to: {palette_id}")
        
        self.current_palette = palette_id
        
        for segment in self.segments.values():
            if hasattr(segment, 'calculate_rgb'):
                segment.rgb_color = segment.calculate_rgb(self.current_palette)
                logger.info(f"Updated segment {segment.segment_ID} colors with palette {palette_id}")
        
    def add_segment(self, segment_ID: int, segment: LightSegment):
        """
        Add a segment of light to the effect.
        
        Args:
            segment_ID: Unique identifier for the segment
            segment: LightSegment instance to add
        """
        self.segments[segment_ID] = segment
        
        if hasattr(segment, 'calculate_rgb'):
            segment.rgb_color = segment.calculate_rgb(self.current_palette)
        
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
        led_transparency = [0.0 for _ in range(self.led_count)] 
        
        from config import DEFAULT_COLOR_PALETTES
        palette = DEFAULT_COLOR_PALETTES.get(self.current_palette, DEFAULT_COLOR_PALETTES["A"])

        sorted_segments = sorted(self.segments.items(), key=lambda item: item[0])

        for segment_id, segment in sorted_segments:
            segment_light_data = segment.get_light_data(palette)

            for led_idx, (segment_color, segment_transparency) in segment_light_data.items():
                if 0 <= led_idx < self.led_count:
                    
                    current_led_color = led_colors[led_idx]
                    current_led_transparency = led_transparency[led_idx] 

                    final_transparency = segment_transparency + current_led_transparency * (1.0 - segment_transparency)
                    final_transparency = max(0.0, min(1.0, final_transparency)) # Clamp to [0, 1]

                    final_color = [0, 0, 0]
                    if final_transparency > 1e-6: 
                        for i in range(3): 
                            final_color[i] = int(
                                (segment_color[i] * segment_transparency + 
                                 current_led_color[i] * current_led_transparency * (1.0 - segment_transparency)) / final_transparency
                            )
                        final_color = [max(0, min(255, c)) for c in final_color]
                    else:
                        final_color = [0, 0, 0] 

                    led_colors[led_idx] = final_color
                    led_transparency[led_idx] = final_transparency
        
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
            "time": 0.0,
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
