from typing import Dict, List, Any, Optional
import re
import sys
import threading
import json
from pythonosc import dispatcher, osc_server, udp_client

sys.path.append('..')
from models.light_effect import LightEffect
from models.light_segment import LightSegment
from models.light_scene import LightScene
from config import (
    DEFAULT_LED_COUNT,
    DEFAULT_FPS,
    DEFAULT_TRANSPARENCY,
    DEFAULT_LENGTH,
    DEFAULT_MOVE_SPEED, 
    DEFAULT_MOVE_RANGE, 
    DEFAULT_INITIAL_POSITION, 
    DEFAULT_IS_EDGE_REFLECT, 
    DEFAULT_DIMMER_TIME
)


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

class OSCHandler:
    """
    OSCHandler manages OSC communication for controlling light scenes, effects, and segments.
    It handles receiving OSC messages, updating the appropriate objects, and sending responses.
    """
    
    def __init__(self, light_scenes: Dict[int, LightScene] = None, ip: str = "127.0.0.1", port: int = 5005):
        """
        Initialize the OSC handler.
        
        Args:
            light_scenes: Dictionary mapping scene_ID to LightScene instances (creates default if None)
            ip: IP address to listen on
            port: Port to listen on
        """
        self.light_scenes = light_scenes or {1: LightScene(scene_ID=1)}
        self.ip = ip
        self.port = port
        
        self.dispatcher = dispatcher.Dispatcher()
        self.setup_dispatcher()
        
        self.server = None
        self.server_thread = None
        
        self.client = udp_client.SimpleUDPClient(ip, port)
        
        self.simulator = None
    
    def setup_dispatcher(self):
        """
        Set up the OSC message dispatcher with appropriate message handlers.
        """
        self.dispatcher.map("/scene/*/effect/*/segment/*/*", self.scene_effect_segment_callback)
        self.dispatcher.map("/scene/*/effect/*/set_palette", self.scene_effect_palette_callback)
        self.dispatcher.map("/scene/*/set_palette", self.scene_palette_callback)
        self.dispatcher.map("/scene/*/update_palettes", self.scene_update_palettes_callback)
        self.dispatcher.map("/scene/*/save_effects", self.scene_save_effects_callback)
        self.dispatcher.map("/scene/*/load_effects", self.scene_load_effects_callback)
        self.dispatcher.map("/scene/*/save_palettes", self.scene_save_palettes_callback)
        self.dispatcher.map("/scene/*/load_palettes", self.scene_load_palettes_callback)
        
        self.dispatcher.map("/effect/*/segment/*/*", self.legacy_effect_segment_callback)
        self.dispatcher.map("/effect/*/object/*/*", self.legacy_effect_object_callback)
        self.dispatcher.map("/palette/*", self.legacy_palette_callback)
        self.dispatcher.map("/request/init", self.init_callback)
    
    def start_server(self):
        """
        Start the OSC server in a separate thread.
        """
        try:
            self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            logger.info(f"OSC server started on {self.ip}:{self.port}")
        except Exception as e:
            logger.info(f"Error starting OSC server: {e}")
            
    def stop_server(self):
        """
        Stop the OSC server.
        """
        if self.server:
            self.server.shutdown()
            logger.info("OSC server stopped")

    def set_simulator(self, simulator):
        """
        Set the simulator instance for UI updates.
        
        Args:
            simulator: The simulator instance
        """
        self.simulator = simulator
    
    def scene_effect_segment_callback(self, address, *args):
        """
        Handle OSC messages for updating segment parameters within a scene.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/scene/(\d+)/effect/(\d+)/segment/(\d+)/(.+)"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        effect_id = int(match.group(2))
        segment_id = int(match.group(3))
        param_name = match.group(4)
        value = args[0]
        
        if scene_id not in self.light_scenes:
            logger.info(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        if effect_id not in scene.effects:
            logger.info(f"Effect {effect_id} not found in scene {scene_id}")
            return
        
        effect = scene.effects[effect_id]
        
        if segment_id not in effect.segments:
            logger.info(f"Segment {segment_id} not found in effect {effect_id}")
            return
        
        segment = effect.segments[segment_id]
        ui_updated = False

        if param_name == "color":
            if isinstance(value, dict):
                if "colors" in value:
                    segment.update_param("color", value["colors"])
                    logger.info(f"Updated colors: {value['colors']}")
                    ui_updated = True
                    
                if "speed" in value:
                    segment.update_param("move_speed", value["speed"])
                    logger.info(f"Updated speed: {value['speed']}")
                    ui_updated = True
                    
                if "gradient" in value:
                    segment.update_param("gradient", value["gradient"] == 1)
                    logger.info(f"Updated gradient: {value['gradient']}")
                    ui_updated = True
                    
            elif isinstance(value, list) and len(value) >= 1:
                segment.update_param("color", value)
                logger.info(f"Updated colors directly: {value}")
                ui_updated = True

        elif param_name == "position":
            if isinstance(value, dict):
                if "initial_position" in value:
                    segment.update_param("initial_position", value["initial_position"])
                    segment.update_param("current_position", float(value["initial_position"]))
                    logger.info(f"Updated position: {value['initial_position']}")
                    ui_updated = True
                    
                if "speed" in value:
                    segment.update_param("move_speed", value["speed"])
                    logger.info(f"Updated speed: {value['speed']}")
                    ui_updated = True
                    
                if "range" in value and isinstance(value["range"], list) and len(value["range"]) == 2:
                    segment.update_param("move_range", value["range"])
                    logger.info(f"Updated range: {value['range']}")
                    ui_updated = True
                    
                if "interval" in value:
                    segment.update_param("position_interval", value["interval"])
                    logger.info(f"Updated interval: {value['interval']}")
                    ui_updated = True

        elif param_name == "span":
            if isinstance(value, dict):
                if "span" in value:
                    new_length = [value["span"]//3, value["span"]//3, value["span"]//3]
                    segment.update_param("length", new_length)
                    logger.info(f"Updated span length: {new_length}")
                    ui_updated = True
                    
                if "range" in value and isinstance(value["range"], list) and len(value["range"]) == 2:
                    segment.update_param("span_range", value["range"])
                    logger.info(f"Updated span range: {value['range']}")
                    ui_updated = True
                    
                if "speed" in value:
                    segment.update_param("span_speed", value["speed"])
                    logger.info(f"Updated span speed: {value['speed']}")
                    ui_updated = True
                    
                if "interval" in value:
                    segment.update_param("span_interval", value["interval"])
                    logger.info(f"Updated span interval: {value['interval']}")
                    ui_updated = True
                    
                if "gradient_colors" in value and isinstance(value["gradient_colors"], list):
                    segment.update_param("gradient_colors", value["gradient_colors"])
                    logger.info(f"Updated gradient colors: {value['gradient_colors']}")
                    ui_updated = True
                    
                if "fade" in value:
                    segment.update_param("fade", value["fade"] == 1)
                    logger.info(f"Updated fade: {value['fade']}")
                    ui_updated = True

        elif param_name == "transparency":
            if isinstance(value, list):
                segment.update_param("transparency", value)
                logger.info(f"Updated transparency: {value}")
                ui_updated = True

        elif param_name == "dimmer_time":
            if isinstance(value, list) and len(value) >= 5:
                segment.update_param("dimmer_time", value)
                logger.info(f"Updated dimmer_time: {value}")
                ui_updated = True
                
        elif param_name == "dimmer_time_ratio":
            if isinstance(value, (int, float)):
                ratio = max(0.1, float(value))
                segment.update_param("dimmer_time_ratio", ratio)
                logger.info(f"Updated dimmer_time_ratio: {ratio}")
                ui_updated = True

        elif param_name == "is_edge_reflect":
            segment.update_param("is_edge_reflect", bool(value))
            logger.info(f"Updated is_edge_reflect: {value}")
            ui_updated = True

        else:
            segment.update_param(param_name, value)
            logger.info(f"Updated {param_name}: {value}")
            ui_updated = True
            
        if ui_updated and self.simulator:
            self._update_simulator(scene_id, effect_id, segment_id)
    
    def scene_effect_palette_callback(self, address, *args):
        """
        Handle OSC messages for setting a palette for a specific effect.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/scene/(\d+)/effect/(\d+)/set_palette"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        effect_id = int(match.group(2))
        palette_id = args[0]
        
        if scene_id not in self.light_scenes:
            logger.info(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        if effect_id not in scene.effects:
            logger.info(f"Effect {effect_id} not found in scene {scene_id}")
            return
        
        if palette_id in scene.palettes:
            scene.effects[effect_id].set_palette(palette_id)
            logger.info(f"Set palette for effect {effect_id} to {palette_id}")
            
            if self.simulator:
                self._update_simulator(scene_id, effect_id)
    
    def scene_palette_callback(self, address, *args):
        """
        Handle OSC messages for setting the current palette for a scene.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/scene/(\d+)/set_palette"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        palette_id = args[0]
        
        if scene_id not in self.light_scenes:
            logger.info(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        if palette_id in scene.palettes:
            scene.set_palette(palette_id)
            logger.info(f"Set palette for scene {scene_id} to {palette_id}")
            
            if self.simulator:
                self._update_simulator(scene_id)
    
    def scene_update_palettes_callback(self, address, *args):
        """
        Handle OSC messages for updating all palettes in a scene.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/scene/(\d+)/update_palettes"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        new_palettes = args[0]
        
        if scene_id not in self.light_scenes:
            logger.info(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        if isinstance(new_palettes, dict):
            scene.update_all_palettes(new_palettes)
            logger.info(f"Updated palettes for scene {scene_id}")
            
            if self.simulator:
                self._update_simulator(scene_id)
    
    def scene_save_effects_callback(self, address, *args):
        """
        Handle OSC messages for saving effects to a JSON file.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/scene/(\d+)/save_effects"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        file_path = args[0]
        
        if scene_id not in self.light_scenes:
            logger.info(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        try:
            scene.save_to_json(file_path)
            logger.info(f"Saved effects configuration to {file_path}")
        except Exception as e:
            logger.info(f"Error saving effects configuration: {e}")
    
    def scene_load_effects_callback(self, address, *args):
        """
        Handle OSC messages for loading effects from a JSON file.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/scene/(\d+)/load_effects"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        file_path = args[0]
        
        try:
            new_scene = LightScene.load_from_json(file_path)
            new_scene.scene_ID = scene_id
            self.light_scenes[scene_id] = new_scene
            logger.info(f"Loaded effects configuration from {file_path}")
            
            if self.simulator:
                self._update_simulator(scene_id)
        except Exception as e:
            logger.info(f"Error loading effects configuration: {e}")
    
    def scene_save_palettes_callback(self, address, *args):
        """
        Handle OSC messages for saving palettes to a JSON file.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/scene/(\d+)/save_palettes"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        file_path = args[0]
        
        if scene_id not in self.light_scenes:
            logger.info(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        try:
            scene.save_palettes_to_json(file_path)
            logger.info(f"Saved palettes to {file_path}")
        except Exception as e:
            logger.info(f"Error saving palettes: {e}")
    
    def scene_load_palettes_callback(self, address, *args):
        """
        Handle OSC messages for loading palettes from a JSON file.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/scene/(\d+)/load_palettes"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        file_path = args[0]
        
        if scene_id not in self.light_scenes:
            logger.info(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        try:
            scene.load_palettes_from_json(file_path)
            logger.info(f"Loaded palettes from {file_path}")
            
            if self.simulator:
                self._update_simulator(scene_id)
        except Exception as e:
            logger.info(f"Error loading palettes: {e}")
    
    def legacy_effect_segment_callback(self, address, *args):
        """
        Handle legacy OSC messages for backward compatibility.
        Maps to new scene-based structure internally.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/effect/(\d+)/segment/(\d+)/(.+)"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        effect_id = int(match.group(1))
        segment_id = int(match.group(2))
        param_name = match.group(3)
        value = args[0]
        
        scene_id = 1
        
        if scene_id not in self.light_scenes:
            self.light_scenes[scene_id] = LightScene(scene_ID=scene_id)
        
        scene = self.light_scenes[scene_id]
        
        if effect_id not in scene.effects:
            scene.add_effect(effect_id, LightEffect(effect_ID=effect_id, led_count=DEFAULT_LED_COUNT, fps=DEFAULT_FPS))
        
        effect = scene.effects[effect_id]
        
        if segment_id not in effect.segments:
            new_segment = LightSegment(
                segment_ID=segment_id,
                color=[0, 1, 2, 3],
                transparency=DEFAULT_TRANSPARENCY,
                length=DEFAULT_LENGTH,
                move_speed=DEFAULT_MOVE_SPEED,
                move_range=DEFAULT_MOVE_RANGE,
                initial_position=DEFAULT_INITIAL_POSITION,
                is_edge_reflect=DEFAULT_IS_EDGE_REFLECT,
                dimmer_time=DEFAULT_DIMMER_TIME,
                dimmer_time_ratio=1.0  
            )
            effect.add_segment(segment_id, new_segment)
        
        new_address = f"/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/{param_name}"
        self.scene_effect_segment_callback(new_address, *args)
    
    def legacy_effect_object_callback(self, address, *args):
        """
        Handle legacy OSC messages with 'object' instead of 'segment'.
        Maps to new scene-based structure internally.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/effect/(\d+)/object/(\d+)/(.+)"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid address pattern: {address}")
            return
            
        effect_id = int(match.group(1))
        object_id = int(match.group(2))
        param_name = match.group(3)
        value = args[0]
        
        scene_id = 1
        
        if scene_id not in self.light_scenes:
            self.light_scenes[scene_id] = LightScene(scene_ID=scene_id)
        
        scene = self.light_scenes[scene_id]
        
        if effect_id not in scene.effects:
            scene.add_effect(effect_id, LightEffect(effect_ID=effect_id, led_count=DEFAULT_LED_COUNT, fps=DEFAULT_FPS))
        
        effect = scene.effects[effect_id]
        
        if object_id not in effect.segments:
            new_segment = LightSegment(
                segment_ID=object_id,
                color=[0, 1, 2, 3],  
                transparency=DEFAULT_TRANSPARENCY,
                length=DEFAULT_LENGTH,
                move_speed=DEFAULT_MOVE_SPEED,
                move_range=DEFAULT_MOVE_RANGE,
                initial_position=DEFAULT_INITIAL_POSITION,
                is_edge_reflect=DEFAULT_IS_EDGE_REFLECT,
                dimmer_time=DEFAULT_DIMMER_TIME,
                dimmer_time_ratio=1.0  
            )
            effect.add_segment(object_id, new_segment)
        
        new_address = f"/scene/{scene_id}/effect/{effect_id}/segment/{object_id}/{param_name}"
        self.scene_effect_segment_callback(new_address, *args)
    
    def legacy_palette_callback(self, address, *args):
        """
        Handle legacy OSC messages for updating palettes.
        Maps to new scene-based structure internally.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        pattern = r"/palette/([A-E])"
        match = re.match(pattern, address)
        
        if not match:
            logger.info(f"Invalid palette address: {address}")
            return
            
        palette_id = match.group(1)
        colors_flat = args[0]
        
        if not isinstance(colors_flat, list) or len(colors_flat) % 3 != 0:
            logger.info(f"Invalid color data for palette {palette_id}: {colors_flat}")
            return
        
        colors = []
        for i in range(0, len(colors_flat), 3):
            r = max(0, min(255, int(colors_flat[i])))
            g = max(0, min(255, int(colors_flat[i+1])))
            b = max(0, min(255, int(colors_flat[i+2])))
            colors.append([r, g, b])
        
        for scene_id, scene in self.light_scenes.items():
            scene.update_palette(palette_id, colors)
            
        logger.info(f"Updated palette {palette_id} with {len(colors)} colors in all scenes")
        
        if self.simulator:
            self._update_simulator()
    
    def init_callback(self, address, *args):
        """
        Handle initialization request from clients.
        Sends current configuration to the client.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments
        """
        if address != "/request/init" or len(args) == 0 or args[0] != 1:
            return
            
        logger.info("Received initialization request")
        
        for scene_id, scene in self.light_scenes.items():
            for palette_id, colors in scene.palettes.items():
                flat_colors = []
                for color in colors:
                    flat_colors.extend(color)
                self.client.send_message(f"/palette/{palette_id}", flat_colors)
            
            for effect_id, effect in scene.effects.items():
                for segment_id, segment in effect.segments.items():
                    self.client.send_message(
                        f"/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/color", 
                        {
                            "colors": segment.color,
                            "speed": segment.move_speed,
                            "gradient": 1 if hasattr(segment, 'gradient') and segment.gradient else 0
                        }
                    )
                    
                    self.client.send_message(
                        f"/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/position",
                        {
                            "initial_position": segment.initial_position,
                            "speed": segment.move_speed,
                            "range": segment.move_range,
                            "interval": getattr(segment, 'position_interval', 10)
                        }
                    )
                    
                    self.client.send_message(
                        f"/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/span",
                        {
                            "span": sum(segment.length),
                            "range": getattr(segment, 'span_range', segment.move_range), 
                            "speed": getattr(segment, 'span_speed', segment.move_speed),
                            "interval": getattr(segment, 'span_interval', 10),
                            "gradient_colors": segment.gradient_colors if hasattr(segment, "gradient_colors") else [0, -1, -1],
                            "fade": 1 if hasattr(segment, 'fade') and segment.fade else 0
                        }
                    )
                    
                    self.client.send_message(
                        f"/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/transparency", 
                        segment.transparency
                    )
                    
                    self.client.send_message(
                        f"/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/is_edge_reflect", 
                        1 if segment.is_edge_reflect else 0
                    )
                    
                    self.client.send_message(
                        f"/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/dimmer_time",
                        segment.dimmer_time
                    )
                    
                    if hasattr(segment, 'dimmer_time_ratio'):
                        self.client.send_message(
                            f"/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/dimmer_time_ratio",
                            segment.dimmer_time_ratio
                        )
                    
                    self.client.send_message(
                        f"/effect/{effect_id}/segment/{segment_id}/color", 
                        {
                            "colors": segment.color,
                            "speed": segment.move_speed,
                            "gradient": 1 if hasattr(segment, 'gradient') and segment.gradient else 0
                        }
                    )
                    
                    self.client.send_message(
                        f"/effect/{effect_id}/object/{segment_id}/color", 
                        {
                            "colors": segment.color,
                            "speed": segment.move_speed,
                            "gradient": 1 if hasattr(segment, 'gradient') and segment.gradient else 0
                        }
                    )
                    
                    self.client.send_message(
                        f"/effect/{effect_id}/object/{segment_id}/position/initial_position", 
                        segment.initial_position
                    )
                    
                    self.client.send_message(
                        f"/effect/{effect_id}/object/{segment_id}/position/speed", 
                        segment.move_speed
                    )
                    
                    self.client.send_message(
                        f"/effect/{effect_id}/object/{segment_id}/position/range", 
                        segment.move_range
                    )
        
        logger.info("Sent initialization data")
        
    def _update_simulator(self, scene_id=None, effect_id=None, segment_id=None):
        """
        Update the simulator UI after parameter changes.
        
        Args:
            scene_id: ID of the scene that changed
            effect_id: ID of the effect that changed
            segment_id: ID of the segment that changed
        """
        if not self.simulator:
            return

        if hasattr(self.simulator, 'ui_dirty'):
            self.simulator.ui_dirty = True
            
        if hasattr(self.simulator, 'active_scene_id') and scene_id is not None:
            self.simulator.active_scene_id = scene_id
            
        if hasattr(self.simulator, 'active_effect_id') and effect_id is not None:
            self.simulator.active_effect_id = effect_id
            
        if hasattr(self.simulator, 'active_segment_id') and segment_id is not None:
            self.simulator.active_segment_id = segment_id