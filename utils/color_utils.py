"""
Utility functions for color manipulation and processing.
These functions handle color interpolation, blending, transparency, and brightness adjustments.
"""

from typing import List, Tuple, Dict, Any

def interpolate_colors(color1: List[int], color2: List[int], factor: float) -> List[int]:
    """
    Interpolate between two RGB colors.
    
    Args:
        color1: First RGB color [r, g, b]
        color2: Second RGB color [r, g, b]
        factor: Interpolation factor (0.0 = color1, 1.0 = color2)
    
    Returns:
        Interpolated RGB color [r, g, b]
    """
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)

    return [max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))]

def apply_transparency(base_color: List[int], overlay_color: List[int], 
                       transparency: float) -> List[int]:
    """
    Apply a transparent overlay color to a base color.
    
    Args:
        base_color: Base RGB color [r, g, b]
        overlay_color: Overlay RGB color [r, g, b]
        transparency: Transparency of the overlay (0.0 = fully transparent, 1.0 = fully opaque)
    
    Returns:
        Resulting RGB color [r, g, b]
    """
    return interpolate_colors(base_color, overlay_color, transparency)

def blend_colors(colors: List[List[int]], weights: List[float]) -> List[int]:
    """
    Blend multiple colors based on weights.
    
    Args:
        colors: List of RGB colors [[r, g, b], ...]
        weights: List of weights for each color [w1, w2, ...]
    
    Returns:
        Blended RGB color [r, g, b]
    """
    if not colors or not weights or len(colors) != len(weights):
        return [0, 0, 0]
        
    total_weight = sum(weights)
    if total_weight == 0:
        return [0, 0, 0]
        
    normalized_weights = [w / total_weight for w in weights]
    
    r = int(sum(c[0] * w for c, w in zip(colors, normalized_weights)))
    g = int(sum(c[1] * w for c, w in zip(colors, normalized_weights)))
    b = int(sum(c[2] * w for c, w in zip(colors, normalized_weights)))
    
    return [max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))]

def apply_brightness(color: List[int], brightness: float) -> List[int]:
    """
    Apply brightness factor to color.
    
    Args:
        color: RGB color [r, g, b]
        brightness: Brightness factor (0.0-1.0)
    
    Returns:
        Resulting RGB color [r, g, b]
    """
    r = int(color[0] * brightness)
    g = int(color[1] * brightness)
    b = int(color[2] * brightness)
    return [max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))]

def get_color_from_palette(palette: Dict[str, List[List[int]]], 
                           palette_name: str, color_index: int) -> List[int]:
    """
    Get a color from a palette by name and index.
    
    Args:
        palette: Dictionary of color palettes
        palette_name: Name of the palette (A, B, C, etc.)
        color_index: Index of the color in the palette (0-5)
    
    Returns:
        RGB color [r, g, b]
    """
    if palette_name not in palette:
        return [0, 0, 0]
    
    palette_colors = palette[palette_name]
    if color_index < 0 or color_index >= len(palette_colors):
        return [0, 0, 0]
    
    return palette_colors[color_index]
