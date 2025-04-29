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
    DEFAULT_DIMMER_TIME,
    IN_PORT,
    OUT_PORT,
    MAX_SEGMENTS
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
    
    def __init__(self, light_scenes: Dict[int, LightScene] = None, ip: str = "127.0.0.1", 
                 in_port: int = IN_PORT, out_port: int = OUT_PORT):
        """
        Initialize the OSC handler.
        
        Args:
            light_scenes: Dictionary mapping scene_ID to LightScene instances (creates default if None)
            ip: IP address to listen on
            in_port: Port to listen for incoming OSC messages
            out_port: Port to send outgoing OSC messages (uses in_port if None)
        """
        self.light_scenes = light_scenes or {1: LightScene(scene_ID=1)}
        self.ip = ip
        self.in_port = in_port
        self.out_port = out_port if out_port is not None else in_port
        
        self.dispatcher = dispatcher.Dispatcher()
        self.setup_dispatcher()
        
        self.server = None
        self.server_thread = None
        
        self.client = udp_client.SimpleUDPClient(ip, self.out_port)
        
        self.simulator = None
        logger.info(f"OSC Handler initialized - IN port: {self.in_port}, OUT port: {self.out_port}")
    
    def setup_dispatcher(self):
        """
        Set up the OSC message dispatcher with appropriate message handlers.
        """
        # Scene/Effect/Segment patterns
        self.dispatcher.map("/scene/*/effect/*/segment/*/*", self.scene_effect_segment_callback)
        self.dispatcher.map("/scene/*/effect/*/set_palette", self.scene_effect_palette_callback)
        self.dispatcher.map("/scene/*/set_palette", self.scene_palette_callback)
        self.dispatcher.map("/scene/*/update_palettes", self.scene_update_palettes_callback)
        self.dispatcher.map("/scene/*/save_effects", self.scene_save_effects_callback)
        self.dispatcher.map("/scene/*/load_effects", self.scene_load_effects_callback)
        self.dispatcher.map("/scene/*/save_palettes", self.scene_save_palettes_callback)
        self.dispatcher.map("/scene/*/load_palettes", self.scene_load_palettes_callback)
        
        # Effect Management
        self.dispatcher.map("/scene/*/add_effect", self.scene_add_effect_callback)
        self.dispatcher.map("/scene/*/remove_effect", self.scene_remove_effect_callback)
        
        # Segment Management
        self.dispatcher.map("/scene/*/effect/*/add_segment", self.scene_effect_add_segment_callback)
        self.dispatcher.map("/scene/*/effect/*/remove_segment", self.scene_effect_remove_segment_callback)
        
        # Scene Manager patterns
        self.dispatcher.map("/scene_manager/add_scene", self.scene_manager_add_scene_callback)
        self.dispatcher.map("/scene_manager/remove_scene", self.scene_manager_remove_scene_callback)
        self.dispatcher.map("/scene_manager/switch_scene", self.scene_manager_switch_scene_callback)
        self.dispatcher.map("/scene_manager/list_scenes", self.scene_manager_list_scenes_callback)
        
        # Legacy patterns
        self.dispatcher.map("/effect/*/segment/*/*", self.legacy_effect_segment_callback)
        self.dispatcher.map("/effect/*/object/*/*", self.legacy_effect_object_callback)
        self.dispatcher.map("/palette/*", self.legacy_palette_callback)
        self.dispatcher.map("/request/init", self.init_callback)
    
    def start_server(self):
        """
        Start the OSC server in a separate thread.
        """
        try:
            self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.in_port), self.dispatcher)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            logger.info(f"OSC server started on {self.ip}:{self.in_port}, sending responses to port {self.out_port}")
        except Exception as e:
            logger.error(f"Error starting OSC server: {e}")
            
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
    
    def scene_add_effect_callback(self, address, *args):
        """
        Handle OSC messages for adding a new effect to a scene.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments (effect_ID)
        """
        pattern = r"/scene/(\d+)/add_effect"
        match = re.match(pattern, address)
        
        if not match:
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        
        if len(args) < 1:
            logger.warning("Missing effect_ID parameter")
            return
            
        try:
            effect_id = int(args[0])
            
            logger.info(f"Received add_effect request: Scene {scene_id}, Effect {effect_id}")
            
            if scene_id not in self.light_scenes:
                logger.warning(f"Scene {scene_id} not found")
                return
                
            scene = self.light_scenes[scene_id]
            
            if effect_id in scene.effects:
                logger.warning(f"Effect {effect_id} already exists in scene {scene_id}")
                return
                
            from config import DEFAULT_LED_COUNT, DEFAULT_FPS
            effect = LightEffect(effect_ID=effect_id, led_count=DEFAULT_LED_COUNT, fps=DEFAULT_FPS)
            
            from models.light_segment import LightSegment
            from config import (
                DEFAULT_TRANSPARENCY, DEFAULT_LENGTH, DEFAULT_MOVE_SPEED,
                DEFAULT_MOVE_RANGE, DEFAULT_INITIAL_POSITION, DEFAULT_IS_EDGE_REFLECT,
                DEFAULT_DIMMER_TIME
            )
            
            segment = LightSegment(
                segment_ID=1,
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
            
            effect.add_segment(1, segment)
            scene.add_effect(effect_id, effect)
            
            logger.info(f"Added effect {effect_id} to scene {scene_id}")
            
            if self.simulator:
                self._update_simulator(scene_id, effect_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Added effect {effect_id} into scene {scene_id}")
            
            self.client.send_message(f"/scene/{scene_id}/effect_added", effect_id)
            
        except Exception as e:
            logger.error(f"Error adding effect: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Error while adding effect: {e}")

    def scene_remove_effect_callback(self, address, *args):
        """
        Handle OSC messages for removing an effect from a scene.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments (effect_ID)
        """
        pattern = r"/scene/(\d+)/remove_effect"
        match = re.match(pattern, address)
        
        if not match:
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        
        if len(args) < 1:
            logger.warning("Missing effect_ID parameter")
            return
            
        try:
            effect_id = int(args[0])
            
            logger.info(f"Received remove_effect request: Scene {scene_id}, Effect {effect_id}")
            
            if scene_id not in self.light_scenes:
                logger.warning(f"Scene {scene_id} not found")
                return
                
            scene = self.light_scenes[scene_id]
            
            if effect_id not in scene.effects:
                logger.warning(f"Effect {effect_id} not found in scene {scene_id}")
                return
                
            if len(scene.effects) <= 1:
                logger.warning(f"Cannot remove the last effect from scene {scene_id}")
                return
                
            if scene.current_effect_ID == effect_id:
                other_effects = [eid for eid in scene.effects.keys() if eid != effect_id]
                if other_effects:
                    scene.current_effect_ID = other_effects[0]
            
            del scene.effects[effect_id]
            
            logger.info(f"Removed effect {effect_id} from scene {scene_id}")
            
            if self.simulator:
                self._update_simulator(scene_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Đã xóa effect {effect_id} khỏi scene {scene_id}")
            
            self.client.send_message(f"/scene/{scene_id}/effect_removed", effect_id)
            
        except Exception as e:
            logger.error(f"Error removing effect: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Lỗi khi xóa effect: {e}")

    def scene_effect_palette_callback(self, address, *args):
        """
        Handle OSC messages for setting the current palette for a specific effect within a scene.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments (palette_ID)
        """
        pattern = r"/scene/(\d+)/effect/(\d+)/set_palette"
        match = re.match(pattern, address)
        
        if not match:
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        effect_id = int(match.group(2))
        
        if len(args) < 1:
            logger.warning("Missing palette_ID parameter")
            return
            
        palette_id = args[0]
        
        logger.info(f"Received OSC: {address} - Palette: {palette_id}")
        
        if scene_id not in self.light_scenes:
            logger.warning(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        if effect_id not in scene.effects:
            logger.warning(f"Effect {effect_id} not found in scene {scene_id}")
            return
            
        effect = scene.effects[effect_id]
        
        if isinstance(palette_id, str) and palette_id in scene.palettes:
            effect.current_palette = palette_id
            for segment in effect.segments.values():
                if hasattr(segment, 'calculate_rgb'):
                    segment.rgb_color = segment.calculate_rgb(palette_id)
            
            if self.simulator:
                self._update_simulator(scene_id, effect_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Effect {effect_id} palette changed to {palette_id}")
        else:
            logger.warning(f"Invalid palette ID: {palette_id} or palette not found in scene {scene_id}")

    def scene_effect_add_segment_callback(self, address, *args):
        """
        Handle OSC messages for adding a new segment to an effect.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments (segment_ID)
        """

        pattern = r"/scene/(\d+)/effect/(\d+)/add_segment"
        match = re.match(pattern, address)
        
        if not match:
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        effect_id = int(match.group(2))
        
        if len(args) < 1:
            segment_id = 1
        else:
            try:
                segment_id = int(args[0])
            except:
                logger.warning(f"Invalid segment ID: {args[0]}")
                segment_id = 1
        
        logger.info(f"Received add_segment request: Scene {scene_id}, Effect {effect_id}, Segment {segment_id}")
        
        if scene_id not in self.light_scenes:
            logger.warning(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        if effect_id not in scene.effects:
            logger.warning(f"Effect {effect_id} not found in scene {scene_id}")
            return
            
        effect = scene.effects[effect_id]
        
        if len(effect.segments) >= MAX_SEGMENTS:
            logger.warning(f"Maximum segment limit ({MAX_SEGMENTS}) reached for effect {effect_id}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Đã đạt giới hạn tối đa {MAX_SEGMENTS} segment")
            return
        
        while segment_id in effect.segments:
            segment_id += 1
        
        try:
            from models.light_segment import LightSegment
            from config import (
                DEFAULT_TRANSPARENCY, DEFAULT_LENGTH, DEFAULT_MOVE_SPEED,
                DEFAULT_MOVE_RANGE, DEFAULT_INITIAL_POSITION, DEFAULT_IS_EDGE_REFLECT,
                DEFAULT_DIMMER_TIME
            )
            
            segment = LightSegment(
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
            
            segment.fade = True
            
            effect.add_segment(segment_id, segment)
            
            logger.info(f"Added segment {segment_id} to effect {effect_id} in scene {scene_id}")
            
            if self.simulator:
                self._update_simulator(scene_id, effect_id, segment_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Added segment {segment_id} into effect {effect_id}")
            
            self.client.send_message(f"/scene/{scene_id}/effect/{effect_id}/segment_added", segment_id)
            
        except Exception as e:
            logger.error(f"Error adding segment: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Error while adding segment: {e}")

    def scene_effect_remove_segment_callback(self, address, *args):
        """
        Handle OSC messages for removing a segment from an effect.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments (segment_ID)
        """
        pattern = r"/scene/(\d+)/effect/(\d+)/remove_segment"
        match = re.match(pattern, address)
        
        if not match:
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        effect_id = int(match.group(2))
        
        if len(args) < 1:
            logger.warning("Missing segment_ID parameter")
            return
            
        try:
            segment_id = int(args[0])
            
            logger.info(f"Received remove_segment request: Scene {scene_id}, Effect {effect_id}, Segment {segment_id}")
            
            if scene_id not in self.light_scenes:
                logger.warning(f"Scene {scene_id} not found")
                return
                
            scene = self.light_scenes[scene_id]
            
            if effect_id not in scene.effects:
                logger.warning(f"Effect {effect_id} not found in scene {scene_id}")
                return
                
            effect = scene.effects[effect_id]
            
            if segment_id not in effect.segments:
                logger.warning(f"Segment {segment_id} not found in effect {effect_id}")
                return
                
            if len(effect.segments) <= 1:
                logger.warning(f"Cannot remove the last segment from effect {effect_id}")
                return
                
            effect.remove_segment(segment_id)
            
            logger.info(f"Removed segment {segment_id} from effect {effect_id} in scene {scene_id}")
            
            if self.simulator:
                if hasattr(self.simulator, 'active_segment_id') and self.simulator.active_segment_id == segment_id:
                    other_segment_id = min(effect.segments.keys())
                    self.simulator.active_segment_id = other_segment_id
                
                self._update_simulator(scene_id, effect_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Đã xóa segment {segment_id} khỏi effect {effect_id}")
            
            self.client.send_message(f"/scene/{scene_id}/effect/{effect_id}/segment_removed", segment_id)
            
        except Exception as e:
            logger.error(f"Error removing segment: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Lỗi khi xóa segment: {e}")

    def scene_manager_list_scenes_callback(self, address, *args):
        """
        Handle OSC messages for listing all available scenes.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments (unused)
        """
        if address != "/scene_manager/list_scenes":
            return
            
        logger.info("Received list_scenes request")
        
        try:
            scene_list = sorted(self.light_scenes.keys())
            
            self.client.send_message("/scene_manager/scenes", scene_list)
            
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Danh sách scene: {scene_list}")
            
            logger.info(f"Sent list of scenes: {scene_list}")
            
        except Exception as e:
            logger.error(f"Error listing scenes: {e}")

    def scene_effect_segment_callback(self, address, *args):
        """
        Handle OSC messages for updating segment parameters within a scene.
        """
        pattern = r"/scene/(\d+)/effect/(\d+)/segment/(\d+)/(.+)"
        match = re.match(pattern, address)
        
        if not match:
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        effect_id = int(match.group(2))
        segment_id = int(match.group(3))
        param_name = match.group(4)
        value = args[0]
        
        logger.info(f"Received OSC: {address} - Args type: {type(args[0])} - Values: {args}")
        
        if scene_id not in self.light_scenes:
            logger.warning(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        if effect_id not in scene.effects:
            logger.warning(f"Effect {effect_id} not found in scene {scene_id}")
            return
        
        effect = scene.effects[effect_id]
        
        if segment_id not in effect.segments:
            logger.warning(f"Segment {segment_id} not found in effect {effect_id}")
            return
        
        segment = effect.segments[segment_id]
        ui_updated = False

        if param_name in ["color", "move_range", "transparency", "dimmer_time", "length"] and isinstance(value, str):
            try:
                if '[' in value and ']' in value:
                    value = json.loads(value)
                else:
                    value = [int(x) if x.strip().isdigit() or (x.strip()[0] == '-' and x.strip()[1:].isdigit()) 
                            else float(x) if '.' in x 
                            else x 
                            for x in value.replace(',', ' ').split()]
                
                logger.info(f"Converted string to list: {value}")
            except Exception as e:
                logger.error(f"Failed to convert string to list: {e}")

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
                    
            elif isinstance(value, list):
                segment.update_param("color", value)
                logger.info(f"Updated colors directly: {value}")
                ui_updated = True
                
            elif isinstance(value, (int, float)):
                current_colors = segment.color.copy()
                current_colors[0] = int(value)
                segment.update_param("color", current_colors)
                logger.info(f"Updated first color to: {value}")
                ui_updated = True

        elif param_name == "move_range":
            if isinstance(value, list) and len(value) >= 2:
                range_min = min(value[0], value[1])
                range_max = max(value[0], value[1])
                segment.update_param("move_range", [range_min, range_max])
                logger.info(f"Updated move_range to [{range_min}, {range_max}]")
                ui_updated = True
            elif isinstance(value, (int, float)):
                current_range = segment.move_range.copy()
                current_range[1] = int(value)
                range_min = min(current_range[0], current_range[1])
                range_max = max(current_range[0], current_range[1])
                segment.update_param("move_range", [range_min, range_max])
                logger.info(f"Updated move_range max to {value}, resulting range: [{range_min}, {range_max}]")
                ui_updated = True

        elif param_name == "transparency":
            if isinstance(value, list):
                segment.update_param("transparency", value)
                logger.info(f"Updated transparency: {value}")
                ui_updated = True
            elif isinstance(value, (int, float)):
                value = max(0.0, min(1.0, float(value)))
                segment.update_param("transparency", [value] * len(segment.transparency))
                logger.info(f"Updated all transparency values to {value}")
                ui_updated = True

        elif param_name == "dimmer_time":
            if isinstance(value, list) and len(value) >= 5:
                segment.update_param("dimmer_time", value)
                logger.info(f"Updated dimmer_time: {value}")
                ui_updated = True
            elif isinstance(value, (int, float)):
                current_dimmer = segment.dimmer_time.copy()
                current_dimmer[4] = int(value)
                segment.update_param("dimmer_time", current_dimmer)
                logger.info(f"Updated dimmer_time cycle to {value}")
                ui_updated = True
                
        elif param_name == "dimmer_time_ratio":
            if isinstance(value, (int, float)):
                ratio = max(0.1, float(value))
                segment.update_param("dimmer_time_ratio", ratio)
                logger.info(f"Updated dimmer_time_ratio: {ratio}")
                ui_updated = True
            elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                ratio = max(0.1, float(value))
                segment.update_param("dimmer_time_ratio", ratio)
                logger.info(f"Updated dimmer_time_ratio from string: {ratio}")
                ui_updated = True

        elif param_name == "is_edge_reflect":
            reflect_value = True
            if isinstance(value, bool):
                reflect_value = value
            elif isinstance(value, (int, float)):
                reflect_value = value != 0
            elif isinstance(value, str):
                reflect_value = value.lower() in ('true', 'yes', '1', 'on')
                
            segment.update_param("is_edge_reflect", reflect_value)
            logger.info(f"Updated is_edge_reflect: {reflect_value}")
            ui_updated = True

        elif param_name == "move_speed":
            if isinstance(value, (int, float)):
                segment.update_param("move_speed", float(value))
                logger.info(f"Updated move_speed: {value}")
                ui_updated = True
            elif isinstance(value, str) and value.replace('-', '', 1).replace('.', '', 1).isdigit():
                speed = float(value)
                segment.update_param("move_speed", speed)
                logger.info(f"Updated move_speed from string: {speed}")
                ui_updated = True
        
        else:
            segment.update_param(param_name, value)
            logger.info(f"Updated {param_name}: {value}")
            ui_updated = True
            
        if ui_updated and self.simulator:
            self._update_simulator(scene_id, effect_id, segment_id)
    
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
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        palette_id = args[0]
        
        logger.info(f"Received OSC: {address} - {args}")
        
        if scene_id not in self.light_scenes:
            logger.warning(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        if isinstance(palette_id, str) and palette_id in scene.palettes:
            scene.set_palette(palette_id)
            logger.info(f"Set palette for scene {scene_id} to {palette_id}")
            
            if self.simulator:
                self._update_simulator(scene_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Scene {scene_id} palette changed to {palette_id}")
        else:
            logger.warning(f"Invalid palette ID: {palette_id}")
    
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
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        new_palettes = args[0]
        
        logger.info(f"Received OSC: {address}")
        
        if scene_id not in self.light_scenes:
            logger.warning(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        if isinstance(new_palettes, dict):
            scene.update_all_palettes(new_palettes)
            logger.info(f"Updated palettes for scene {scene_id}")
            
            if self.simulator:
                self._update_simulator(scene_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Updated palettes for scene {scene_id}")
    
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
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        file_path = args[0]
        
        logger.info(f"Received OSC: {address} - {args}")
        
        if scene_id not in self.light_scenes:
            logger.warning(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        try:
            for effect in scene.effects.values():
                effect.time = 0.0
                for segment in effect.segments.values():
                    if hasattr(segment, 'time'):
                        segment.time = 0.0
                        
            scene.save_to_json(file_path)
            logger.info(f"Saved effects configuration to {file_path}")
            
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Saved effects to {file_path}")
        except Exception as e:
            logger.error(f"Error saving effects configuration: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Error saving: {e}")
    
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
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        file_path = args[0]
        
        logger.info(f"Received OSC: {address} - {args}")
        
        try:
            new_scene = LightScene.load_from_json(file_path)
            new_scene.scene_ID = scene_id
            self.light_scenes[scene_id] = new_scene
            logger.info(f"Loaded effects configuration from {file_path}")
            
            if self.simulator:
                self._update_simulator(scene_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Loaded effects from {file_path}")
        except Exception as e:
            logger.error(f"Error loading effects configuration: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Error loading: {e}")
    
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
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        file_path = args[0]
        
        logger.info(f"Received OSC: {address} - {args}")
        
        if scene_id not in self.light_scenes:
            logger.warning(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        try:
            scene.save_palettes_to_json(file_path)
            logger.info(f"Saved palettes to {file_path}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Đã lưu bảng màu vào {file_path}")
        except Exception as e:
            logger.error(f"Error saving palettes: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Lỗi khi lưu bảng màu: {e}")
    
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
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        scene_id = int(match.group(1))
        file_path = args[0]
        
        logger.info(f"Received OSC: {address} - {args}")
        
        if scene_id not in self.light_scenes:
            logger.warning(f"Scene {scene_id} not found")
            return
            
        scene = self.light_scenes[scene_id]
        
        try:
            scene.load_palettes_from_json(file_path)
            logger.info(f"Loaded palettes from {file_path}")
            
            if self.simulator:
                self._update_simulator(scene_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Đã tải bảng màu từ {file_path}")
        except Exception as e:
            logger.error(f"Error loading palettes: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Lỗi khi tải bảng màu: {e}")
    
    def scene_manager_add_scene_callback(self, address, *args):
        """
        Handle OSC messages for adding a new scene.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments (scene_ID)
        """
        if address != "/scene_manager/add_scene" or not args:
            return
            
        try:
            scene_id = int(args[0])
            logger.info(f"Received add_scene request for scene {scene_id}")
            
            if scene_id in self.light_scenes:
                logger.warning(f"Scene {scene_id} already exists")
                return
                
            from config import DEFAULT_LED_COUNT, DEFAULT_FPS
            
            new_scene = LightScene(scene_ID=scene_id)
            effect = LightEffect(effect_ID=1, led_count=DEFAULT_LED_COUNT, fps=DEFAULT_FPS)
            
            from config import (
                DEFAULT_TRANSPARENCY, DEFAULT_LENGTH, DEFAULT_MOVE_SPEED,
                DEFAULT_MOVE_RANGE, DEFAULT_INITIAL_POSITION, DEFAULT_IS_EDGE_REFLECT,
                DEFAULT_DIMMER_TIME
            )
            
            segment = LightSegment(
                segment_ID=1,
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
            
            segment.gradient = False
            segment.fade = True 
            
            effect.add_segment(1, segment)
            new_scene.add_effect(1, effect)
            
            self.light_scenes[scene_id] = new_scene
            logger.info(f"Added new scene with ID {scene_id}")
            
            if self.simulator:
                self._update_simulator(scene_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Đã tạo scene mới với ID {scene_id}")
            
            self.client.send_message("/scene_manager/scene_added", scene_id)
            
        except Exception as e:
            logger.error(f"Error adding scene: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Lỗi khi tạo scene: {e}")
    
    def scene_manager_remove_scene_callback(self, address, *args):
        """
        Handle OSC messages for removing a scene.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments (scene_ID)
        """
        if len(self.light_scenes) <= 1:
            logger.warning("Cannot remove the last remaining scene")
            return
        
        if address != "/scene_manager/remove_scene" or not args:
            return
            
        try:
            scene_id = int(args[0])
            logger.info(f"Received remove_scene request for scene {scene_id}")
            
            if scene_id not in self.light_scenes:
                logger.warning(f"Scene {scene_id} does not exist")
                return
                
            if len(self.light_scenes) <= 1:
                logger.warning("Cannot remove the last remaining scene")
                return
                
            del self.light_scenes[scene_id]
            logger.info(f"Removed scene with ID {scene_id}")
            
            if self.simulator and hasattr(self.simulator, 'active_scene_id') and self.simulator.active_scene_id == scene_id:
                remaining_scene_id = next(iter(self.light_scenes.keys()))
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Đã xóa scene {scene_id}, chuyển sang scene {remaining_scene_id}")
                self._update_simulator(remaining_scene_id)
            elif self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Đã xóa scene {scene_id}")
            
            self.client.send_message("/scene_manager/scene_removed", scene_id)
            
        except Exception as e:
            logger.error(f"Error removing scene: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Lỗi khi xóa scene: {e}")
    
    def scene_manager_switch_scene_callback(self, address, *args):
        """
        Handle OSC messages for switching the active scene.
        
        Args:
            address: OSC address pattern
            *args: OSC message arguments (scene_ID)
        """
        if address != "/scene_manager/switch_scene" or not args:
            return
            
        try:
            scene_id = int(args[0])
            logger.info(f"Received switch_scene request to scene {scene_id}")
            
            if scene_id not in self.light_scenes:
                logger.warning(f"Scene {scene_id} does not exist")
                return
            
            if self.simulator:
                self._update_simulator(scene_id)
                if hasattr(self.simulator, '_add_notification'):
                    self.simulator._add_notification(f"Đã chuyển sang scene {scene_id}")
            
            self.client.send_message("/scene_manager/scene_switched", scene_id)
            
        except Exception as e:
            logger.error(f"Error switching scene: {e}")
            if self.simulator and hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Lỗi khi chuyển scene: {e}")
    
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
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        effect_id = int(match.group(1))
        segment_id = int(match.group(2))
        param_name = match.group(3)
        value = args[0]
        
        logger.info(f"Received legacy OSC: {address} - {args}")
        
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
            logger.warning(f"Invalid address pattern: {address}")
            return
            
        effect_id = int(match.group(1))
        object_id = int(match.group(2))
        param_name = match.group(3)
        value = args[0]
        
        logger.info(f"Received legacy OSC: {address} - {args}")
        
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
            logger.warning(f"Invalid palette address: {address}")
            return
            
        palette_id = match.group(1)
        colors_flat = args[0]
        
        logger.info(f"Received legacy palette update: {address}")
        
        if not isinstance(colors_flat, list) or len(colors_flat) % 3 != 0:
            logger.warning(f"Invalid color data for palette {palette_id}: {colors_flat}")
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
            if hasattr(self.simulator, '_add_notification'):
                self.simulator._add_notification(f"Đã cập nhật bảng màu {palette_id}")
    
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
            
        if hasattr(self.simulator, 'scene') and scene_id is not None:
            if scene_id in self.light_scenes:
                self.simulator.scene = self.light_scenes[scene_id]
            
        if hasattr(self.simulator, 'active_scene_id') and scene_id is not None:
            self.simulator.active_scene_id = scene_id
            
        if hasattr(self.simulator, 'active_effect_id') and effect_id is not None:
            self.simulator.active_effect_id = effect_id
            
        if hasattr(self.simulator, 'active_segment_id') and segment_id is not None:
            self.simulator.active_segment_id = segment_id
