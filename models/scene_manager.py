import json
import copy
from typing import Dict, List, Any, Optional

from models.light_scene import LightScene
from models.light_effect import LightEffect
from models.light_segment import LightSegment


import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("color_signal_system")

class SceneManager:
    
    def __init__(self):
        """Khởi tạo SceneManager."""
        self.scenes = {}
        self.current_scene = None
        self.next_scene_idx = None
        self.next_effect_idx = None
        self.next_palette_idx = None
        self.fade_in_time = 0.0
        self.fade_out_time = 0.0
        self.transition_start_time = 0.0
        self.is_transitioning = False
        self.transition_opacity = 1.0
        self.osc_handler = None
        
    def add_scene(self, scene_ID: int, scene: LightScene):
        self.scenes[scene_ID] = scene
        
        if self.current_scene is None:
            self.current_scene = scene_ID
    
    def remove_scene(self, scene_ID: int):

        if scene_ID in self.scenes:
            if scene_ID == self.current_scene:
                if len(self.scenes) > 1:
                    other_scenes = [sid for sid in self.scenes.keys() if sid != scene_ID]
                    self.current_scene = other_scenes[0]
                else:
                    self.current_scene = None
            
            del self.scenes[scene_ID]
    
    def switch_scene(self, scene_ID: int):
        if scene_ID in self.scenes:
            if self.fade_in_time > 0 or self.fade_out_time > 0:
                self.next_scene_idx = scene_ID
                self.is_transitioning = True
                self.transition_start_time = 0.0
                self.transition_opacity = 0.0
            else:
                self.current_scene = scene_ID
                self.next_scene_idx = None
    
    def set_transition_params(self, next_scene_idx, next_effect_idx, next_palette_idx, fade_in_time, fade_out_time):
        self.next_scene_idx = next_scene_idx
        self.next_effect_idx = next_effect_idx
        self.next_palette_idx = next_palette_idx
        self.fade_in_time = max(0, fade_in_time)
        self.fade_out_time = max(0, fade_out_time)
        
        if next_scene_idx is not None or next_effect_idx is not None or next_palette_idx is not None:
            self.is_transitioning = True
            self.transition_start_time = 0.0
            self.transition_opacity = 0.0
    
    def update(self):
        if self.current_scene is None or self.current_scene not in self.scenes:
            return
        
        current_scene = self.scenes[self.current_scene]
        
        if self.is_transitioning:
            self.transition_start_time += 1.0 / current_scene.effects[current_scene.current_effect_ID].fps if current_scene.current_effect_ID in current_scene.effects else 0.03
            
            if self.transition_start_time <= self.fade_out_time:
                self.transition_opacity = 1.0 - (self.transition_start_time / self.fade_out_time)
            
            elif self.transition_start_time <= self.fade_out_time + 0.1:
                self.transition_opacity = 0.0
                
                if self.transition_start_time >= self.fade_out_time:
                    if self.next_scene_idx is not None and self.next_scene_idx in self.scenes:
                        self.current_scene = self.next_scene_idx
                    
                    current_scene = self.scenes[self.current_scene]
                    
                    if self.next_effect_idx is not None:
                        if self.next_effect_idx in current_scene.effects:
                            current_scene.switch_effect(self.next_effect_idx)
                    
                    if self.next_palette_idx is not None:
                        if isinstance(self.next_palette_idx, str) and self.next_palette_idx in current_scene.palettes:
                            current_scene.set_palette(self.next_palette_idx)
                        elif isinstance(self.next_palette_idx, int) and 0 <= self.next_palette_idx < len(current_scene.palettes):
                            palette_ids = sorted(current_scene.palettes.keys())
                            current_scene.set_palette(palette_ids[self.next_palette_idx])
            
            elif self.transition_start_time <= self.fade_out_time + 0.1 + self.fade_in_time:
                elapsed = self.transition_start_time - (self.fade_out_time + 0.1)
                self.transition_opacity = elapsed / self.fade_in_time
            else:
                self.transition_opacity = 1.0
                self.is_transitioning = False
                self.next_scene_idx = None
                self.next_effect_idx = None
                self.next_palette_idx = None

        current_scene.update()

        if hasattr(self, 'osc_handler') and self.osc_handler is not None:
            self.osc_handler.send_led_binary_data()
    
    def set_scene_manager_osc_handler(self):
        if self.simulator and hasattr(self.simulator, 'scene_manager'):
            self.simulator.scene_manager.osc_handler = self
            logger.info("Registered OSCHandler with SceneManager for LED binary output")

    def get_led_output(self):
        if self.current_scene is None or self.current_scene not in self.scenes:
            return []
    
        led_colors = self.scenes[self.current_scene].get_led_output()
        
        if self.is_transitioning and self.transition_opacity < 1.0:
            for i in range(len(led_colors)):
                led_colors[i] = [
                    int(c * self.transition_opacity) for c in led_colors[i]
                ]
        
        return led_colors
    
    def save_scenes_to_json(self, file_path: str):
        data = {
            "scenes": [],
            "current_scene": self.current_scene,
            "transition_params": {
                "fade_in_time": self.fade_in_time,
                "fade_out_time": self.fade_out_time
            }
        }
        
        for scene_id, scene in self.scenes.items():
            scene_data = {
                "scene_ID": scene.scene_ID,
                "current_effect_ID": scene.current_effect_ID,
                "current_palette": scene.current_palette,
                "palettes": scene.palettes,
                "effects": {}
            }
            
            for effect_id, effect in scene.effects.items():
                effect_data = {
                    "effect_ID": effect.effect_ID,
                    "led_count": effect.led_count,
                    "fps": effect.fps,
                    "segments": {}
                }
                
                for segment_id, segment in effect.segments.items():
                    segment_data = segment.to_dict()
                    effect_data["segments"][str(segment_id)] = segment_data
                
                scene_data["effects"][str(effect_id)] = effect_data
            
            data["scenes"].append(scene_data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def load_scenes_from_json(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.scenes = {}
        
            for scene_data in data.get("scenes", []):
                scene = LightScene(scene_ID=scene_data["scene_ID"])
        
                if "palettes" in scene_data:
                    scene.palettes = scene_data["palettes"]
                if "current_palette" in scene_data:
                    scene.current_palette = scene_data["current_palette"]
                
                for effect_id_str, effect_data in scene_data.get("effects", {}).items():
                    effect_id = int(effect_id_str)
                    effect = LightEffect(
                        effect_ID=effect_id,
                        led_count=effect_data["led_count"],
                        fps=effect_data["fps"]
                    )
                    
                    for segment_id_str, segment_data in effect_data.get("segments", {}).items():
                        segment_id = int(segment_id_str)
                        segment = LightSegment.from_dict(segment_data)
                        effect.add_segment(segment_id, segment)
                    
                    scene.add_effect(effect_id, effect)
                
                if "current_effect_ID" in scene_data and scene_data["current_effect_ID"] is not None:
                    scene.current_effect_ID = scene_data["current_effect_ID"]
                elif scene.effects:
                    scene.current_effect_ID = min(scene.effects.keys())
                
                self.add_scene(scene.scene_ID, scene)
            
            if "current_scene" in data and data["current_scene"] is not None and data["current_scene"] in self.scenes:
                self.current_scene = data["current_scene"]
            elif self.scenes:
                self.current_scene = min(self.scenes.keys())
            
            if "transition_params" in data:
                self.fade_in_time = data["transition_params"].get("fade_in_time", 0.0)
                self.fade_out_time = data["transition_params"].get("fade_out_time", 0.0)
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải file JSON: {str(e)}")
            return False
            
    def create_new_scene(self, scene_ID: int = None):
        if scene_ID is None:
            scene_ID = 1
            while scene_ID in self.scenes:
                scene_ID += 1
        
        scene = LightScene(scene_ID=scene_ID)
        
        from config import DEFAULT_LED_COUNT, DEFAULT_FPS
        effect = LightEffect(effect_ID=1, led_count=DEFAULT_LED_COUNT, fps=DEFAULT_FPS)
        
        from config import DEFAULT_TRANSPARENCY, DEFAULT_LENGTH, DEFAULT_MOVE_SPEED
        from config import DEFAULT_MOVE_RANGE, DEFAULT_INITIAL_POSITION, DEFAULT_IS_EDGE_REFLECT, DEFAULT_DIMMER_TIME
        
        segment = LightSegment(
            segment_ID=1,
            color=[0, 1, 2, 3],
            transparency=DEFAULT_TRANSPARENCY,
            length=DEFAULT_LENGTH,
            move_speed=DEFAULT_MOVE_SPEED,
            move_range=DEFAULT_MOVE_RANGE,
            initial_position=DEFAULT_INITIAL_POSITION,
            is_edge_reflect=DEFAULT_IS_EDGE_REFLECT,
            dimmer_time=DEFAULT_DIMMER_TIME
        )
        
        effect.add_segment(1, segment)
        scene.add_effect(1, effect)
        
        self.add_scene(scene_ID, scene)
        
        return scene_ID