from typing import Dict, List, Any, Optional
import json
import sys
sys.path.append('..')
from models.light_effect import LightEffect
from models.light_segment import LightSegment
from config import DEFAULT_COLOR_PALETTES

class LightScene:
    """
    LightScene manages multiple LightEffect instances and shares color palettes among them.
    
    Note: This class is an extension to the base specification which only defines LightSegment
    and LightEffect. It provides higher-level management for multiple effects and color palettes.
    """
    
    def __init__(self, scene_ID: int):
        """
        Initialize a LightScene instance.
        
        Args:
            scene_ID: Unique identifier for this scene
        """
        self.scene_ID = scene_ID
        self.effects: Dict[int, LightEffect] = {}
        self.current_effect_ID = None
        self.palettes = DEFAULT_COLOR_PALETTES.copy()
        self.current_palette = "A"
        self.next_effect_idx = None
        self.next_palette_idx = None
        self.fade_in_time = 0.0
        self.fade_out_time = 0.0
        self.transition_start_time = 0.0
        self.effect_transition_active = False
        self.palette_transition_active = False
        
    def add_effect(self, effect_ID: int, effect: LightEffect):
        """
        Add a LightEffect to the scene.
        
        Args:
            effect_ID: Unique identifier for the effect
            effect: LightEffect instance to add
        """
        self.effects[effect_ID] = effect
        effect.current_palette = self.current_palette
        
        if self.current_effect_ID is None:
            self.current_effect_ID = effect_ID
    
    def remove_effect(self, effect_ID: int):
        """
        Remove a LightEffect from the scene.
        
        Args:
            effect_ID: ID of the effect to remove
        """
        if effect_ID in self.effects:
            del self.effects[effect_ID]

            if effect_ID == self.current_effect_ID:
                if self.effects:
                    self.current_effect_ID = next(iter(self.effects.keys()))
                else:
                    self.current_effect_ID = None
    
    def set_palette(self, palette_id: str):
        """
        Change the current color palette for all effects.
        
        Args:
            palette_id: ID of the palette to use
        """
        if palette_id in self.palettes:
            self.current_palette = palette_id

            for effect in self.effects.values():
                effect.set_palette(palette_id)
    
    def update_palette(self, palette_id: str, colors: List[List[int]]):
        """
        Update a specific palette's colors.
        
        Args:
            palette_id: ID of the palette to update
            colors: New color values
        """
        if palette_id in self.palettes:
            self.palettes[palette_id] = colors

            if palette_id == self.current_palette:
                self.set_palette(palette_id)
    
    def update_all_palettes(self, new_palettes: Dict[str, List[List[int]]]):
        """
        Update all palettes at once.
        
        Args:
            new_palettes: Dictionary of palette_id -> color list
        """
        self.palettes = new_palettes.copy()
        
        if self.current_palette in self.palettes:
            self.set_palette(self.current_palette)
        elif self.palettes:

            self.current_palette = next(iter(self.palettes.keys()))
            self.set_palette(self.current_palette)
    
    def switch_effect(self, effect_ID: int):
        """
        Switch to a different LightEffect.
        
        Args:
            effect_ID: ID of the effect to switch to
        """
        if effect_ID in self.effects:
            self.current_effect_ID = effect_ID
    
    def update(self):
        """
        Update the current LightEffect.
        Delegates to the active effect's update_all method.
        """

        if hasattr(self, 'effect_transition_active') and self.effect_transition_active:
            self.transition_start_time += 1.0 / self.effects[self.current_effect_ID].fps
            
            if self.transition_start_time >= self.fade_out_time + self.fade_in_time:
                if self.next_effect_idx is not None and self.next_effect_idx in self.effects:
                    self.switch_effect(self.next_effect_idx)
                
                self.effect_transition_active = False
                self.next_effect_idx = None
                self.transition_start_time = 0.0
        
        if hasattr(self, 'palette_transition_active') and self.palette_transition_active:
            self.transition_start_time += 1.0 / self.effects[self.current_effect_ID].fps
            
            if self.transition_start_time >= self.fade_out_time + self.fade_in_time:
                if self.next_palette_idx is not None:
                    self.set_palette(self.next_palette_idx)
                
                self.palette_transition_active = False
                self.next_palette_idx = None
                self.transition_start_time = 0.0

                if hasattr(self, '_notify_palette_change'):
                    self._notify_palette_change()
        
        if self.current_effect_ID is not None and self.current_effect_ID in self.effects:
            self.effects[self.current_effect_ID].update_all()
    
    def get_led_output(self) -> List[List[int]]:
        """
        Get the LED output from the current effect.
        
        Returns:
            List of RGB color values for each LED
        """
        if self.current_effect_ID is not None and self.current_effect_ID in self.effects:
            return self.effects[self.current_effect_ID].get_led_output()
        return []

    def set_transition_params(self, next_effect_idx=None, next_palette_idx=None, fade_in_time=0.0, fade_out_time=0.0):
        self.next_effect_idx = next_effect_idx
        self.next_palette_idx = next_palette_idx
        self.fade_in_time = fade_in_time
        self.fade_out_time = fade_out_time
        
        self.transition_start_time = 0.0
        self.effect_transition_active = next_effect_idx is not None
        self.palette_transition_active = next_palette_idx is not None
    
    def save_to_json(self, file_path: str):
        """
        Save the complete scene configuration to a JSON file.
        
        Args:
            file_path: Path to save the JSON file
        """
        data = {
            "scene_ID": self.scene_ID,
            "current_effect_ID": self.current_effect_ID,
            "current_palette": self.current_palette,
            "palettes": self.palettes,
            "effects": {}
        }
        
        for effect_id, effect in self.effects.items():
            effect_data = effect.to_dict()
            data["effects"][str(effect_id)] = effect_data
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    @classmethod
    def load_from_json(cls, file_path: str):
        """
        Load a scene configuration from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            A new LightScene instance with the loaded configuration
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        scene = cls(scene_ID=data["scene_ID"])
        
        if "palettes" in data:
            scene.palettes = data["palettes"]
        
        if "current_palette" in data:
            scene.current_palette = data["current_palette"]

        for effect_id_str, effect_data in data["effects"].items():
            effect_id = int(effect_id_str)
            effect = LightEffect.from_dict(effect_data)
            scene.add_effect(effect_id, effect)
        
        if "current_effect_ID" in data and data["current_effect_ID"] is not None:
            scene.current_effect_ID = data["current_effect_ID"]
            
        return scene
    
    def save_palettes_to_json(self, file_path: str):
        """
        Save only color palettes to a JSON file.
        
        Args:
            file_path: Path to save the JSON file
        """
        data = {
            "palettes": self.palettes,
            "current_palette": self.current_palette
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    def load_palettes_from_json(self, file_path: str):
        """
        Load color palettes from a JSON file.
        
        Args:
            file_path: Path to the JSON file
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if "palettes" in data:
            self.palettes = data["palettes"]
        
        if "current_palette" in data:
            self.set_palette(data["current_palette"])