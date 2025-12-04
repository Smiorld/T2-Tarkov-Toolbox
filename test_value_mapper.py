"""
Test script for the ValueMapper system.

This validates that all UI value combinations are safe and won't cause saturation.
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from modules.screen_filter.models import FilterConfig
from modules.screen_filter.value_mapper import ValueMapper


def test_ui_ranges():
    """Test that all UI range extremes are valid"""
    print("=== Testing UI Range Extremes ===\n")

    # Test brightness extremes
    print("Testing Brightness Range:")
    for brightness_ui in [-100, -50, 0, 50, 100]:
        brightness_algo = ValueMapper.ui_to_algo_brightness(brightness_ui)
        print(f"  UI: {brightness_ui:4} -> Algo: {brightness_algo:6.3f}")

    print("\nTesting Contrast Range:")
    for contrast_ui in [-50, -25, 0, 25, 50]:
        contrast_algo = ValueMapper.ui_to_algo_contrast(contrast_ui)
        print(f"  UI: {contrast_ui:4} -> Algo: {contrast_algo:6.3f}")

    print("\nTesting Gamma Range:")
    for gamma_ui in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        gamma_algo = ValueMapper.ui_to_algo_gamma(gamma_ui)
        print(f"  UI: {gamma_ui:4.1f} -> Algo: {gamma_algo:6.3f}")

    print("\nTesting RGB Range:")
    for rgb_ui in [0, 64, 128, 192, 255]:
        rgb_algo = ValueMapper.ui_to_algo_rgb(rgb_ui)
        print(f"  UI: {rgb_ui:3} -> Algo: {rgb_algo:6.3f}")


def test_extreme_combinations():
    """Test extreme parameter combinations"""
    print("\n=== Testing Extreme Combinations ===\n")

    test_cases = [
        ("Max Brightness + Max Contrast", 100, 3.0, 50),
        ("Max Brightness + Max Gamma", 100, 3.0, 0),
        ("Max Brightness + Min Gamma", 100, 0.5, 0),
        ("Min Brightness + Max Contrast", -100, 1.0, 50),
        ("Min Brightness + Min Contrast", -100, 1.0, -50),
        ("Balanced High Values", 75, 2.5, 35),
        ("Balanced Low Values", -75, 0.75, -35),
        ("High Gamma + High Contrast", 0, 3.0, 50),
        ("Low Gamma + High Contrast", 0, 0.5, 50),
    ]

    results = []
    for name, brightness_ui, gamma_ui, contrast_ui in test_cases:
        # Convert to algorithm values
        brightness_algo = ValueMapper.ui_to_algo_brightness(brightness_ui)
        gamma_algo = ValueMapper.ui_to_algo_gamma(gamma_ui)
        contrast_algo = ValueMapper.ui_to_algo_contrast(contrast_ui)

        config = FilterConfig(
            brightness=brightness_algo,
            gamma=gamma_algo,
            contrast=contrast_algo,
            red_scale=1.0,
            green_scale=1.0,
            blue_scale=1.0
        )

        is_valid, error_msg = ValueMapper.validate_config(config)

        status = "✓ PASS" if is_valid else "✗ FAIL"
        results.append((name, status, is_valid, error_msg))

        print(f"{status} | {name}")
        print(f"       UI Values: B={brightness_ui:4}, G={gamma_ui:4.1f}, C={contrast_ui:3}")
        print(f"     Algo Values: B={brightness_algo:5.2f}, G={gamma_algo:4.2f}, C={contrast_algo:5.2f}")

        if not is_valid:
            print(f"       Error: {error_msg}")
            safe_config = ValueMapper.suggest_safe_values(config)
            print(f"       Safe Values: B={safe_config.brightness:5.2f}, G={safe_config.gamma:4.2f}, C={safe_config.contrast:5.2f}")

        print()

    # Summary
    print("=== Summary ===")
    passed = sum(1 for _, _, valid, _ in results if valid)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    return passed == total


def test_preset_defaults():
    """Test the default presets"""
    print("\n=== Testing Default Presets ===\n")

    from modules.screen_filter.preset_manager import PresetManager

    manager = PresetManager()
    presets = manager.get_all_presets()

    for preset in presets:
        is_valid, error_msg = ValueMapper.validate_config(preset.config)
        status = "✓ PASS" if is_valid else "✗ FAIL"

        print(f"{status} | {preset.name} ({preset.id})")
        print(f"       B={preset.config.brightness:5.2f}, G={preset.config.gamma:4.2f}, C={preset.config.contrast:5.2f}")

        if not is_valid:
            print(f"       Error: {error_msg}")

        print()


def test_round_trip_conversion():
    """Test that UI -> Algo -> UI conversions are accurate"""
    print("\n=== Testing Round-Trip Conversions ===\n")

    test_values = {
        "brightness": [-100, -50, 0, 50, 100],
        "contrast": [-50, -25, 0, 25, 50],
        "gamma": [0.5, 1.0, 2.0, 3.0],
        "rgb": [0, 64, 128, 192, 255]
    }

    all_pass = True

    # Brightness
    print("Brightness Round-Trip:")
    for ui_val in test_values["brightness"]:
        algo_val = ValueMapper.ui_to_algo_brightness(ui_val)
        back_to_ui = ValueMapper.algo_to_ui_brightness(algo_val)
        diff = abs(ui_val - back_to_ui)
        status = "✓" if diff < 0.1 else "✗"
        print(f"  {status} {ui_val:4} -> {algo_val:6.3f} -> {back_to_ui:6.2f} (diff: {diff:.4f})")
        if diff >= 0.1:
            all_pass = False

    # Contrast
    print("\nContrast Round-Trip:")
    for ui_val in test_values["contrast"]:
        algo_val = ValueMapper.ui_to_algo_contrast(ui_val)
        back_to_ui = ValueMapper.algo_to_ui_contrast(algo_val)
        diff = abs(ui_val - back_to_ui)
        status = "✓" if diff < 0.1 else "✗"
        print(f"  {status} {ui_val:4} -> {algo_val:6.3f} -> {back_to_ui:6.2f} (diff: {diff:.4f})")
        if diff >= 0.1:
            all_pass = False

    # Gamma
    print("\nGamma Round-Trip:")
    for ui_val in test_values["gamma"]:
        algo_val = ValueMapper.ui_to_algo_gamma(ui_val)
        back_to_ui = ValueMapper.algo_to_ui_gamma(algo_val)
        diff = abs(ui_val - back_to_ui)
        status = "✓" if diff < 0.01 else "✗"
        print(f"  {status} {ui_val:4.2f} -> {algo_val:6.3f} -> {back_to_ui:6.3f} (diff: {diff:.4f})")
        if diff >= 0.01:
            all_pass = False

    # RGB
    print("\nRGB Round-Trip:")
    for ui_val in test_values["rgb"]:
        algo_val = ValueMapper.ui_to_algo_rgb(ui_val)
        back_to_ui = ValueMapper.algo_to_ui_rgb(algo_val)
        diff = abs(ui_val - back_to_ui)
        status = "✓" if diff < 0.1 else "✗"
        print(f"  {status} {ui_val:3} -> {algo_val:6.3f} -> {back_to_ui:6.2f} (diff: {diff:.4f})")
        if diff >= 0.1:
            all_pass = False

    print(f"\nRound-trip conversions: {'✓ ALL PASS' if all_pass else '✗ SOME FAILED'}")
    return all_pass


if __name__ == "__main__":
    print("=" * 70)
    print("Value Mapper Validation Test Suite")
    print("=" * 70)

    # Run all tests
    test_ui_ranges()
    all_valid = test_extreme_combinations()
    test_preset_defaults()
    round_trip_ok = test_round_trip_conversion()

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Extreme combinations: {'✓ ALL VALID' if all_valid else '✗ SOME INVALID'}")
    print(f"Round-trip accuracy: {'✓ ALL ACCURATE' if round_trip_ok else '✗ SOME INACCURATE'}")

    if all_valid and round_trip_ok:
        print("\n✓ All tests passed! Value mapping system is working correctly.")
    else:
        print("\n✗ Some tests failed. Please review the results above.")
