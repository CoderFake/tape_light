# Led Tape Light System

A comprehensive system for generating, visualizing, and controlling LED color signals with real-time manipulation capabilities.

## Overview

The Led Tape Light System is designed for creating dynamic light effects for LED installations. It provides a flexible framework for defining light segments with various properties such as color, position, movement, and effects. The system includes a visual simulator for previewing effects and supports OSC (Open Sound Control) for integration with external controllers.

## System Requirements

- Python >= 3.10, <= 3.11
- Required packages listed in requirements.txt

## Installation

1. Create a virtual environment (recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the system with default settings:

```
python main.py
```

### Command Line Options

- `--fps`: Set frames per second (default: 60)
- `--led-count`: Set number of LEDs (default: 225)
- `--osc-ip`: Set OSC IP address (default: 0.0.0.0)
- `--in-port`: Set OSC input port (default: 9090)
- `--out-port`: Set OSC output port (default: 5005)
- `--no-gui`: Run without GUI (headless mode)
- `--simulator-only`: Run only the simulator without OSC
- `--config-file`: Load configuration from a JSON file
- `--scale-factor`: Set UI scale factor (default: 1.2)
- `--japanese-font`: Path to Japanese font file

Example:
```
python main.py --fps 30 --led-count 300 --in-port 8000 --out-port 8001
```

### GUI Controls

The simulator interface provides controls for:

- Selecting and switching between scenes, effects, and segments
- Adjusting segment properties (position, speed, color, etc.)
- Controlling dimmer time and dimmer time ratio
- Changing color palettes
- Zooming and panning the LED view
- Toggling animation playback
- Saving and loading configurations

### Keyboard Shortcuts

- **Space**: Play/Pause animation
- **Left/Right Arrow**: Pan view
- **+/-**: Zoom in/out
- **0**: Reset zoom and pan
- **C**: Center view
- **F**: Toggle fade visualizer
- **I**: Toggle segment indicators
- **Tab**: Cycle through segments
- **Ctrl+S**: Save configuration
- **Ctrl+L/O**: Load configuration

### OSC Control

The system can be controlled remotely via OSC messages. The OSC address patterns follow this structure:

#### Main Patterns:
- `/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/{parameter}`: Control segment parameters
- `/scene/{scene_id}/effect/{effect_id}/set_palette`: Set palette for an effect
- `/scene/{scene_id}/set_palette`: Set palette for a scene
- `/scene/{scene_id}/update_palettes`: Update all palettes in a scene

#### Scene Management:
- `/scene_manager/add_scene`: Add a new scene
- `/scene_manager/remove_scene`: Remove a scene
- `/scene_manager/switch_scene`: Switch to another scene
- `/scene_manager/list_scenes`: Get a list of available scenes

#### Effect Management:
- `/scene/{scene_id}/add_effect`: Add a new effect to a scene
- `/scene/{scene_id}/remove_effect`: Remove an effect from a scene

#### Segment Management:
- `/scene/{scene_id}/effect/{effect_id}/add_segment`: Add a new segment to an effect
- `/scene/{scene_id}/effect/{effect_id}/remove_segment`: Remove a segment from an effect

#### File Operations:
- `/scene/{scene_id}/save_effects`: Save effects to a JSON file
- `/scene/{scene_id}/load_effects`: Load effects from a JSON file
- `/scene/{scene_id}/save_palettes`: Save palettes to a JSON file
- `/scene/{scene_id}/load_palettes`: Load palettes from a JSON file

## Configuration

The system's default settings are defined in `config.py`, including:

- Default FPS and LED count
- OSC communication settings
- Color palettes
- UI settings
- Default segment properties

## System Architecture

The system is organized into several components:

### Key Components

- **LightSegment**: Represents a segment of light with properties like color, position, movement
- **LightEffect**: Manages multiple segments to create a complete lighting effect
- **LightScene**: Organizes multiple effects and manages color palettes
- **SceneManager**: Handles scene transitions and overall system control
- **OSCHandler**: Handles OSC communication for remote control
- **LEDSimulator**: Provides a visual interface for previewing and controlling effects

### Module Structure

- `main.py`: Entry point and application initialization
- `config.py`: Configuration settings
- `models/`: Core data structures
  - `light_segment.py`: LightSegment class
  - `light_effect.py`: LightEffect class
  - `light_scene.py`: LightScene class
  - `scene_manager.py`: SceneManager class
- `controllers/`: Communication handlers
  - `osc_handler.py`: OSC communication
- `ui/`: User interface components
  - `led_simulator.py`: Visual simulator
- `utils/`: Utility functions
  - `color_utils.py`: Color manipulation functions

## Troubleshooting

- If the OSC server fails to start, check that the port isn't in use by another application
- If you see UI scaling issues, adjust the scale factor with the `--scale-factor` option
- Check the application log file (`app.log`) for detailed error messages
- For problems with Japanese text display, provide a Japanese font with the `--japanese-font` option

## Extensions and Customization

To extend the system with new features:

1. For new segment properties, update the `LightSegment` class
2. For new effects, implement them in the `LightEffect` class
3. For UI changes, modify the `LEDSimulator` class
4. For new OSC commands, update the `OSCHandler` class
