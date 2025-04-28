# Color Signal Generation System

A comprehensive system for generating, visualizing, and controlling LED color signals with real-time manipulation capabilities.

## Overview

The Color Signal Generation System is designed for creating dynamic light effects for LED installations. It provides a flexible framework for defining light segments with various properties such as color, position, movement, and effects. The system includes a visual simulator for previewing effects and supports OSC (Open Sound Control) for integration with external controllers.

## Features

- **Dynamic Light Effects**: Create complex light patterns with multiple segments
- **Real-time Control**: Adjust parameters on-the-fly with immediate visual feedback
- **OSC Integration**: Control the system remotely via OSC protocol
- **Visual Simulator**: Preview light effects in a responsive GUI
- **Multiple Color Palettes**: Switch between different color schemes
- **Gradient and Fade Effects**: Apply gradient colors and fading effects to segments
- **Responsive UI**: Interface adapts to different screen sizes and zoom levels

## System Architecture

The system is organized into several components:

- **Models**: Core data structures for light segments, effects, and scenes
- **Controllers**: Handlers for OSC communication
- **UI**: Visual simulator for previewing and controlling effects
- **Utils**: Utility functions for color manipulation

### Key Components

- **LightSegment**: Represents a segment of light with properties like color, position, and movement
- **LightEffect**: Manages multiple segments to create a complete lighting effect
- **LightScene**: Organizes multiple effects and manages color palettes
- **OSCHandler**: Handles OSC communication for remote control
- **LEDSimulator**: Provides a visual interface for previewing and controlling effects

## Installation

1. Clone the repository
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
- `--osc-port`: Set OSC port (default: 9090)
- `--no-gui`: Run without GUI (headless mode)
- `--simulator-only`: Run only the simulator without OSC
- `--config-file`: Load configuration from a JSON file

Example:
```
python main.py --fps 30 --led-count 300 --osc-port 8000
```

### GUI Controls

The simulator interface provides controls for:

- Selecting and switching between effects and segments
- Adjusting segment properties (position, speed, color, etc.)
- Changing color palettes
- Zooming and panning the LED view
- Toggling animation playback

### OSC Control

The system can be controlled remotely via OSC messages. The OSC address patterns follow this structure:

- `/scene/{scene_id}/effect/{effect_id}/segment/{segment_id}/{parameter}`: Control segment parameters
- `/scene/{scene_id}/effect/{effect_id}/set_palette`: Set palette for an effect
- `/scene/{scene_id}/set_palette`: Set palette for a scene
- `/scene/{scene_id}/update_palettes`: Update all palettes in a scene

## Configuration

The system's default settings are defined in `config.py`, including:

- Default FPS and LED count
- OSC communication settings
- Color palettes
- UI settings
- Default segment properties

## Development

### Adding New Features

To extend the system with new features:

1. For new segment properties, update the `LightSegment` class
2. For new effects, implement them in the `LightEffect` class
3. For UI changes, modify the `LEDSimulator` class
4. For new OSC commands, update the `OSCHandler` class

### Code Structure

- `main.py`: Entry point and application initialization
- `config.py`: Configuration settings
- `models/`: Core data structures
- `controllers/`: Communication handlers
- `ui/`: User interface components
- `utils/`: Utility functions

## License

This project is licensed under the MIT License - see the LICENSE file for details.
