DEFAULT_FPS = 60
DEFAULT_LED_COUNT = 225
IN_PORT = 9090
OUT_PORT = 5005
DEFAULT_OSC_IP = "0.0.0.0"

# Color Palettes
DEFAULT_COLOR_PALETTES = {
    "A": [
        [255, 0, 0],    # Red
        [0, 255, 0],    # Green
        [0, 0, 255],    # Blue
        [255, 255, 0],  # Yellow
        [0, 255, 255],  # Cyan
        [255, 0, 255]   # Magenta
    ],
    "B": [
        [255, 128, 0],  # Orange
        [128, 0, 255],  # Purple
        [0, 128, 255],  # Sky Blue
        [255, 0, 128],  # Pink
        [128, 255, 0],  # Lime
        [255, 255, 255] # White
    ],
    "C": [
        [128, 0, 0],    # Dark Red
        [0, 128, 0],    # Dark Green
        [0, 0, 128],    # Dark Blue
        [128, 128, 0],  # Olive
        [0, 128, 128],  # Teal
        [128, 0, 128]   # Purple
    ],
    "D": [
        [255, 200, 200],  # Light Pink
        [200, 255, 200],  # Light Green
        [200, 200, 255],  # Light Blue
        [255, 255, 200],  # Light Yellow
        [200, 255, 255],  # Light Cyan
        [255, 200, 255]   # Light Magenta
    ],
    "E": [
        [100, 100, 100],  # Dark Gray
        [150, 150, 150],  # Medium Gray
        [200, 200, 200],  # Light Gray
        [255, 100, 50],   # Coral
        [50, 100, 255],   # Royal Blue
        [150, 255, 150]   # Light Green
    ]
}


UI_WIDTH = 1400
UI_HEIGHT = 800
UI_BACKGROUND_COLOR = (30, 30, 30)
UI_TEXT_COLOR = (220, 220, 220)
UI_ACCENT_COLOR = (50, 120, 220)
UI_BUTTON_COLOR = (60, 60, 60)

DEFAULT_TRANSPARENCY = [1.0, 1.0, 1.0, 1.0]
DEFAULT_LENGTH = [10, 10, 10]
DEFAULT_MOVE_SPEED = 10.0
DEFAULT_MOVE_RANGE = [0, DEFAULT_LED_COUNT - 1]
DEFAULT_INITIAL_POSITION = 0
DEFAULT_IS_EDGE_REFLECT = True
DEFAULT_DIMMER_TIME = [0, 100, 200, 100, 0]
DEFAULT_DIMMER_TIME_RATIO = 1.0