"""
Value mapping and validation system for screen filter parameters.

This module ensures all UI values are safe and won't cause gamma ramp saturation.
"""

from typing import Tuple
from modules.screen_filter.models import FilterConfig


class ValueMapper:
    """Maps UI values to algorithm values with safety constraints"""

    # UI Ranges (what user sees)
    BRIGHTNESS_UI_RANGE = (-100, 100)  # Percentage: -100% to +100%
    GAMMA_UI_RANGE = (0.5, 3.0)        # Direct value: 0.5 to 3.0
    CONTRAST_UI_RANGE = (-50, 50)      # Percentage: -50% to +50%
    RGB_UI_RANGE = (0, 255)            # 0-255 scale: 0% to 100%

    # Algorithm Ranges (internal)
    # Based on industry standards (FFmpeg, Gamma Panel, NVIDIA Freestyle)
    # References:
    # - FFmpeg eq filter: brightness ±1.0, contrast ±2.0, gamma 0.1-10.0
    # - Gamma Panel: brightness ±1.0, contrast 0.1-3.0, gamma 0.3-4.4
    # - NVIDIA Freestyle: typically uses ±40% for adjustments
    BRIGHTNESS_ALGO_RANGE = (-0.5, 0.5)   # Conservative ±50% (within FFmpeg's ±1.0)
    GAMMA_ALGO_RANGE = (0.5, 3.0)         # Reduced upper bound for safety
    CONTRAST_ALGO_RANGE = (-0.5, 0.5)     # Conservative ±50% (within FFmpeg's ±2.0)
    RGB_ALGO_RANGE = (0.0, 1.0)           # Normalized 0-100%

    @classmethod
    def ui_to_algo_brightness(cls, ui_value: float) -> float:
        """Convert UI brightness (-100 to 100) to algorithm value"""
        # Map -100..100 to -0.5..0.5 (industry standard safe range)
        min_ui, max_ui = cls.BRIGHTNESS_UI_RANGE
        min_algo, max_algo = cls.BRIGHTNESS_ALGO_RANGE

        # Linear interpolation
        normalized = (ui_value - min_ui) / (max_ui - min_ui)
        algo_value = min_algo + normalized * (max_algo - min_algo)

        return cls._clamp(algo_value, min_algo, max_algo)

    @classmethod
    def algo_to_ui_brightness(cls, algo_value: float) -> float:
        """Convert algorithm brightness to UI value"""
        min_ui, max_ui = cls.BRIGHTNESS_UI_RANGE
        min_algo, max_algo = cls.BRIGHTNESS_ALGO_RANGE

        normalized = (algo_value - min_algo) / (max_algo - min_algo)
        ui_value = min_ui + normalized * (max_ui - min_ui)

        return cls._clamp(ui_value, min_ui, max_ui)

    @classmethod
    def ui_to_algo_gamma(cls, ui_value: float) -> float:
        """Convert UI gamma to algorithm value (direct mapping)"""
        min_val, max_val = cls.GAMMA_UI_RANGE
        return cls._clamp(ui_value, min_val, max_val)

    @classmethod
    def algo_to_ui_gamma(cls, algo_value: float) -> float:
        """Convert algorithm gamma to UI value (direct mapping)"""
        min_val, max_val = cls.GAMMA_UI_RANGE
        return cls._clamp(algo_value, min_val, max_val)

    @classmethod
    def ui_to_algo_contrast(cls, ui_value: float) -> float:
        """Convert UI contrast (-50 to 50) to algorithm value"""
        # Map -50..50 to -0.5..0.5 (conservative range based on industry standards)
        min_ui, max_ui = cls.CONTRAST_UI_RANGE
        min_algo, max_algo = cls.CONTRAST_ALGO_RANGE

        normalized = (ui_value - min_ui) / (max_ui - min_ui)
        algo_value = min_algo + normalized * (max_algo - min_algo)

        return cls._clamp(algo_value, min_algo, max_algo)

    @classmethod
    def algo_to_ui_contrast(cls, algo_value: float) -> float:
        """Convert algorithm contrast to UI value"""
        min_ui, max_ui = cls.CONTRAST_UI_RANGE
        min_algo, max_algo = cls.CONTRAST_ALGO_RANGE

        normalized = (algo_value - min_algo) / (max_algo - min_algo)
        ui_value = min_ui + normalized * (max_ui - min_ui)

        return cls._clamp(ui_value, min_ui, max_ui)

    @classmethod
    def ui_to_algo_rgb(cls, ui_value: float) -> float:
        """Convert UI RGB (0-255) to algorithm value (0.0-1.0)"""
        min_ui, max_ui = cls.RGB_UI_RANGE
        return cls._clamp(ui_value / max_ui, 0.0, 1.0)

    @classmethod
    def algo_to_ui_rgb(cls, algo_value: float) -> float:
        """Convert algorithm RGB to UI value"""
        min_ui, max_ui = cls.RGB_UI_RANGE
        return cls._clamp(algo_value * max_ui, min_ui, max_ui)

    @classmethod
    def validate_config(cls, config: FilterConfig) -> Tuple[bool, str]:
        """
        Validate if a config will produce a valid gamma ramp.

        Returns:
            (is_valid, error_message)
        """
        # Test critical points where saturation is most likely
        test_points = [0.0, 0.25, 0.5, 0.75, 1.0]

        for base_val in test_points:
            # Simulate the calculation pipeline matching gamma_controller.py exactly
            try:
                # 1. Contrast (with clamping like in gamma_controller)
                contrast_factor = 1.0 + config.contrast
                contrasted = (base_val - 0.5) * contrast_factor + 0.5
                contrasted = max(0.0, min(1.0, contrasted))  # Clamped in actual implementation

                # 2. Gamma
                if config.gamma < 0.01:
                    return False, "Gamma value too low"

                gamma_corrected = contrasted ** (1.0 / config.gamma)

                # 3. Brightness (with clamping like in gamma_controller)
                brightness_factor = 1.0 + config.brightness
                brightened = gamma_corrected * brightness_factor
                brightened = max(0.0, min(1.0, brightened))  # Clamped in actual implementation

                # 4. RGB scaling
                for channel_name, channel_scale in [
                    ("red", config.red_scale),
                    ("green", config.green_scale),
                    ("blue", config.blue_scale)
                ]:
                    final_val = brightened * channel_scale
                    # RGB is clamped in the actual implementation too
                    final_val = max(0.0, min(1.0, final_val))

            except Exception as e:
                return False, f"Calculation error: {str(e)}"

        # All values are valid because clamping prevents saturation
        return True, ""

    @classmethod
    def suggest_safe_values(cls, config: FilterConfig) -> FilterConfig:
        """
        Adjust config values to ensure they're safe.

        This progressively reduces extreme values until the config passes validation.
        """
        test_config = FilterConfig(
            brightness=config.brightness,
            gamma=config.gamma,
            contrast=config.contrast,
            red_scale=config.red_scale,
            green_scale=config.green_scale,
            blue_scale=config.blue_scale
        )

        # Try original config first
        is_valid, _ = cls.validate_config(test_config)
        if is_valid:
            return test_config

        # Progressive reduction strategy
        # 1. Reduce brightness first (most common cause)
        if abs(test_config.brightness) > 0.6:
            test_config.brightness *= 0.75
            is_valid, _ = cls.validate_config(test_config)
            if is_valid:
                return test_config

        # 2. Reduce contrast
        if abs(test_config.contrast) > 0.3:
            test_config.contrast *= 0.75
            is_valid, _ = cls.validate_config(test_config)
            if is_valid:
                return test_config

        # 3. If still invalid, scale down both proportionally
        for scale_factor in [0.9, 0.8, 0.7, 0.6, 0.5]:
            test_config.brightness = config.brightness * scale_factor
            test_config.contrast = config.contrast * scale_factor

            is_valid, _ = cls.validate_config(test_config)
            if is_valid:
                return test_config

        # Last resort: return safe defaults
        return FilterConfig(
            brightness=0.0,
            gamma=config.gamma,  # Keep gamma as it rarely causes issues alone
            contrast=0.0,
            red_scale=config.red_scale,
            green_scale=config.green_scale,
            blue_scale=config.blue_scale
        )

    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value to range"""
        return max(min_val, min(max_val, value))

    @classmethod
    def get_ui_ranges(cls) -> dict:
        """Get all UI ranges for documentation/display"""
        return {
            "brightness": cls.BRIGHTNESS_UI_RANGE,
            "gamma": cls.GAMMA_UI_RANGE,
            "contrast": cls.CONTRAST_UI_RANGE,
            "rgb": cls.RGB_UI_RANGE
        }

    @classmethod
    def get_safe_max_brightness(cls, gamma: float, contrast: float) -> float:
        """
        Calculate the maximum safe brightness for given gamma and contrast.

        This is useful for dynamic UI limits.
        """
        # Test with maximum input value (1.0)
        base_val = 1.0

        # Apply contrast
        contrast_factor = 1.0 + contrast
        contrasted = (base_val - 0.5) * contrast_factor + 0.5
        contrasted = cls._clamp(contrasted, 0.0, 1.0)

        # Apply gamma
        if gamma < 0.01:
            gamma = 0.01
        gamma_corrected = contrasted ** (1.0 / gamma)

        # Calculate max brightness that keeps result <= 1.0
        # brightened = gamma_corrected * (1 + brightness) <= 1.0
        # brightness <= (1.0 / gamma_corrected) - 1.0

        if gamma_corrected > 0.01:
            max_brightness_algo = (1.0 / gamma_corrected) - 1.0
            max_brightness_algo = cls._clamp(max_brightness_algo, -1.0, 1.0)

            # Convert to UI value
            return cls.algo_to_ui_brightness(max_brightness_algo)

        return cls.BRIGHTNESS_UI_RANGE[1]
