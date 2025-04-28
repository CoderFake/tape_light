import sys
import time
import os
import argparse
import logging
from typing import Dict, List, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("color_signal_system")

from config import (
    DEFAULT_FPS, DEFAULT_LED_COUNT, DEFAULT_OSC_PORT, DEFAULT_OSC_IP,
    DEFAULT_TRANSPARENCY, DEFAULT_LENGTH, DEFAULT_MOVE_SPEED,
    DEFAULT_MOVE_RANGE, DEFAULT_IS_EDGE_REFLECT,
    DEFAULT_DIMMER_TIME, DEFAULT_DIMMER_TIME_RATIO
)
from models.light_segment import LightSegment
from models.light_effect import LightEffect
from models.light_scene import LightScene
from controllers.osc_handler import OSCHandler
from ui.led_simulator import LEDSimulator

def create_default_segments(effect: LightEffect, count: int = 3):
    center_position = effect.led_count // 2 
    for i in range(1, count + 1):
        segment = LightSegment(
            segment_ID=i,
            color=[i % 6, (i + 1) % 6, (i + 2) % 6, (i + 3) % 6], 
            transparency=DEFAULT_TRANSPARENCY,
            length=DEFAULT_LENGTH,
            move_speed=DEFAULT_MOVE_SPEED * (1 if i % 2 == 0 else -1),  
            move_range=DEFAULT_MOVE_RANGE, 
            initial_position=center_position - 30 + i * 30,
            is_edge_reflect=DEFAULT_IS_EDGE_REFLECT,
            dimmer_time=DEFAULT_DIMMER_TIME,
            dimmer_time_ratio=DEFAULT_DIMMER_TIME_RATIO 
        )
        segment.gradient = False
        segment.fade = False
        segment.gradient_colors = [0, -1, -1]
        effect.add_segment(i, segment)


def create_default_effects(scene: LightScene, num_effects: int = 3):
    for effect_id in range(1, num_effects + 1): 
        effect = LightEffect(effect_ID=effect_id, led_count=DEFAULT_LED_COUNT, fps=DEFAULT_FPS)
        create_default_segments(effect, count=3)
        scene.add_effect(effect_id, effect)

def parse_arguments():
    parser = argparse.ArgumentParser(description='LED Color Signal Generator')
    parser.add_argument('--fps', type=int, default=DEFAULT_FPS, help=f'Frames per second (default: {DEFAULT_FPS})')
    parser.add_argument('--led-count', type=int, default=DEFAULT_LED_COUNT, help=f'Number of LEDs (default: {DEFAULT_LED_COUNT})')
    parser.add_argument('--osc-ip', type=str, default=DEFAULT_OSC_IP, help=f'OSC IP address (default: {DEFAULT_OSC_IP})')
    parser.add_argument('--osc-port', type=int, default=DEFAULT_OSC_PORT, help=f'OSC port (default: {DEFAULT_OSC_PORT})')
    parser.add_argument('--no-gui', action='store_true', help='Run without GUI')
    parser.add_argument('--simulator-only', action='store_true', help='Run only the simulator without OSC')
    parser.add_argument('--config-file', type=str, help='Load configuration from a JSON file')
    parser.add_argument('--scale-factor', type=float, default=1.2, help='Scale factor for UI elements (default: 1.2)')
    parser.add_argument('--japanese-font', type=str, help='Path to Japanese font file')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    logger.info("Initializing Color Signal Generation System...")
    logger.info(f"FPS: {args.fps}, LED Count: {args.led_count}, OSC: {args.osc_ip}:{args.osc_port}")
    
    light_scenes = {}
    
    if args.config_file and os.path.exists(args.config_file):
        try:
            scene = LightScene.load_from_json(args.config_file)
            light_scenes[scene.scene_ID] = scene
            logger.info(f"Configuration loaded from {args.config_file}")
        except Exception as e:
            logger.error(f"Error loading configuration from {args.config_file}: {e}")
            logger.info("Creating default scene.")
            scene = LightScene(scene_ID=1)
            create_default_effects(scene)
            light_scenes[scene.scene_ID] = scene
    else:
        scene = LightScene(scene_ID=1)
        create_default_effects(scene)
        light_scenes[scene.scene_ID] = scene
    
    font_dir = os.path.join(current_dir, 'assets', 'fonts')
    os.makedirs(font_dir, exist_ok=True)
    
    japanese_font = args.japanese_font
    if not japanese_font or not os.path.exists(japanese_font):
        japanese_font = os.path.join(font_dir, 'NotoSansJP-Regular.ttf')
        if not os.path.exists(japanese_font):
            logger.warning(f"Japanese font not found. UI may not display Japanese characters properly.")
    
    osc_handler = None
    if not args.simulator_only:
        osc_handler = OSCHandler(light_scenes, ip=args.osc_ip, port=args.osc_port)
        osc_handler.start_server()
    
    try:
        if not args.no_gui:
            logger.info("Starting LED Simulator...")
            active_scene = light_scenes[1]
            simulator = LEDSimulator(scene=active_scene)
            simulator.ui_state['scale_factor'] = args.scale_factor
            
            if os.path.exists(japanese_font):
                simulator.japanese_font_path = japanese_font
                logger.info("Japanese font loaded")
            
            if not args.simulator_only and osc_handler:
                osc_handler.set_simulator(simulator)
            
            simulator.run()
        else:
            logger.info("Running in headless mode (no GUI)...")
            logger.info("Press Ctrl+C to exit")
            
            while True:
                for scene in light_scenes.values():
                    scene.update()
                time.sleep(1.0/args.fps)
                
    except KeyboardInterrupt:
        logger.info("User interrupted. Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if not args.simulator_only and osc_handler:
            osc_handler.stop_server()
        logger.info("System shutdown complete.")

if __name__ == "__main__":
    main()