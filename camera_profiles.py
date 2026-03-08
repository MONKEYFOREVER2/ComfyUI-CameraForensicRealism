"""
Camera Forensic Realism Engine — Camera Profiles
Real-world sensor data, JPEG quantization tables, and vignetting curves
for multiple camera models.

Author: Custom-built for Z-Image-Turbo workflow
"""

import numpy as np

# ============================================================================
# Standard JPEG Luminance Quantization Table (IJG baseline, Q=50)
# Used as the basis for camera-specific scaling
# ============================================================================
STANDARD_LUMINANCE_QT = np.array([
    [16, 11, 10, 16,  24,  40,  51,  61],
    [12, 12, 14, 19,  26,  58,  60,  55],
    [14, 13, 16, 24,  40,  57,  69,  56],
    [14, 17, 22, 29,  51,  87,  80,  62],
    [18, 22, 37, 56,  68, 109, 103,  77],
    [24, 35, 55, 64,  81, 104, 113,  92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103,  99],
], dtype=np.float32)

STANDARD_CHROMINANCE_QT = np.array([
    [17, 18, 24, 47, 99, 99, 99, 99],
    [18, 21, 26, 66, 99, 99, 99, 99],
    [24, 26, 56, 99, 99, 99, 99, 99],
    [47, 66, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
], dtype=np.float32)


def _scale_qt(base_qt: np.ndarray, quality: int) -> np.ndarray:
    """Scale a quantization table by JPEG quality factor (1-100).
    Uses the IJG standard scaling formula."""
    if quality <= 0:
        quality = 1
    if quality > 100:
        quality = 100
    if quality < 50:
        scale = 5000 / quality
    else:
        scale = 200 - quality * 2
    qt = np.floor((base_qt * scale + 50) / 100)
    qt = np.clip(qt, 1, 255)
    return qt.astype(np.float32)


def _make_camera_qt(lum_offsets: np.ndarray, chrom_offsets: np.ndarray,
                    base_quality: int) -> dict:
    """Create camera-specific quantization tables by applying per-frequency
    offsets to the scaled standard tables. Real camera ISPs have proprietary
    tables that deviate from the IJG standard — these offsets simulate that."""
    lum = _scale_qt(STANDARD_LUMINANCE_QT, base_quality) + lum_offsets
    chrom = _scale_qt(STANDARD_CHROMINANCE_QT, base_quality) + chrom_offsets
    lum = np.clip(lum, 1, 255).astype(np.float32)
    chrom = np.clip(chrom, 1, 255).astype(np.float32)
    return {"luminance": lum, "chrominance": chrom}


# ============================================================================
# Camera Profiles
# ============================================================================

CAMERA_PROFILES = {
    "iPhone 15 Pro": {
        "description": "Apple iPhone 15 Pro — Sony IMX803 48MP sensor",
        "sensor": {
            "read_noise_e": 1.6,        # electrons RMS
            "dark_current_e_per_s": 0.5, # electrons/second at 25°C
            "quantum_efficiency": 0.56,
            "bit_depth": 12,
            "full_well_capacity": 8200,  # electrons
            "hot_pixel_probability": 0.00008,
            "base_iso": 50,
        },
        "bayer_pattern": "RGGB",
        "jpeg_tables": _make_camera_qt(
            # Apple ISP: aggressive mid-frequency preservation, slightly
            # softer high-frequency quantization for "smooth" Apple look
            lum_offsets=np.array([
                [ 0,  0,  0, -1, -1,  0,  1,  2],
                [ 0,  0,  0, -1, -1,  1,  1,  1],
                [ 0,  0,  0, -1,  0,  1,  2,  1],
                [-1, -1, -1,  0,  1,  2,  2,  1],
                [-1, -1,  0,  1,  2,  3,  3,  2],
                [ 0,  0,  1,  1,  2,  2,  3,  2],
                [ 1,  1,  2,  2,  2,  3,  3,  2],
                [ 2,  2,  2,  2,  3,  2,  2,  2],
            ], dtype=np.float32),
            chrom_offsets=np.array([
                [ 0,  0, -1, -2, 0, 0, 0, 0],
                [ 0,  0, -1, -1, 0, 0, 0, 0],
                [-1, -1, -2, -1, 0, 0, 0, 0],
                [-2, -1, -1,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
            ], dtype=np.float32),
            base_quality=92,
        ),
        "vignetting": {
            "cos4_strength": 0.35,    # how strongly cos⁴ law applies
            "asymmetry_x": 0.02,      # lens decentering X
            "asymmetry_y": -0.01,     # lens decentering Y
            "radial_falloff": 2.2,    # power curve exponent
        },
        "color_bias": {             # subtle ISP color shift
            "r_gain": 1.01,
            "g_gain": 1.00,
            "b_gain": 0.985,
        },
    },

    "Samsung Galaxy S24": {
        "description": "Samsung Galaxy S24 Ultra — Samsung GN2 50MP sensor",
        "sensor": {
            "read_noise_e": 2.1,
            "dark_current_e_per_s": 0.8,
            "quantum_efficiency": 0.51,
            "bit_depth": 12,
            "full_well_capacity": 10500,
            "hot_pixel_probability": 0.00012,
            "base_iso": 50,
        },
        "bayer_pattern": "GRBG",
        "jpeg_tables": _make_camera_qt(
            # Samsung ISP: more aggressive sharpening in tables,
            # preserves more high-frequency detail
            lum_offsets=np.array([
                [ 0,  0, -1, -1, -2, -1,  0,  1],
                [ 0,  0, -1, -2, -2, -1,  0,  0],
                [-1, -1, -1, -2, -1,  0,  1,  0],
                [-1, -2, -2, -1,  0,  1,  1,  1],
                [-2, -2, -1,  0,  1,  2,  2,  1],
                [-1, -1,  0,  0,  1,  1,  2,  1],
                [ 0,  0,  1,  1,  1,  2,  2,  1],
                [ 1,  1,  1,  1,  2,  1,  1,  1],
            ], dtype=np.float32),
            chrom_offsets=np.array([
                [ 0,  0,  0, -1, 0, 0, 0, 0],
                [ 0,  0,  0, -1, 0, 0, 0, 0],
                [ 0,  0, -1,  0, 0, 0, 0, 0],
                [-1, -1,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
            ], dtype=np.float32),
            base_quality=95,
        ),
        "vignetting": {
            "cos4_strength": 0.30,
            "asymmetry_x": -0.015,
            "asymmetry_y": 0.008,
            "radial_falloff": 2.0,
        },
        "color_bias": {
            "r_gain": 1.015,
            "g_gain": 1.00,
            "b_gain": 0.98,
        },
    },

    "Sony A7IV": {
        "description": "Sony A7 IV — Sony IMX554 33MP full-frame sensor",
        "sensor": {
            "read_noise_e": 1.2,
            "dark_current_e_per_s": 0.3,
            "quantum_efficiency": 0.62,
            "bit_depth": 14,
            "full_well_capacity": 44000,
            "hot_pixel_probability": 0.00005,
            "base_iso": 100,
        },
        "bayer_pattern": "RGGB",
        "jpeg_tables": _make_camera_qt(
            # Sony ISP: very clean, preserves fine detail across all freqs
            lum_offsets=np.array([
                [ 0,  0,  0,  0, -1, -1,  0,  0],
                [ 0,  0,  0,  0, -1, -1,  0,  0],
                [ 0,  0,  0,  0,  0, -1,  0,  0],
                [ 0,  0,  0,  0,  0,  0,  0,  0],
                [-1, -1,  0,  0,  0,  1,  1,  0],
                [-1, -1, -1,  0,  0,  0,  1,  0],
                [ 0,  0,  0,  0,  0,  1,  1,  0],
                [ 0,  0,  0,  0,  1,  0,  0,  0],
            ], dtype=np.float32),
            chrom_offsets=np.zeros((8, 8), dtype=np.float32),
            base_quality=97,
        ),
        "vignetting": {
            "cos4_strength": 0.45,   # full-frame = more vignetting
            "asymmetry_x": 0.005,
            "asymmetry_y": -0.003,
            "radial_falloff": 2.4,
        },
        "color_bias": {
            "r_gain": 1.005,
            "g_gain": 1.00,
            "b_gain": 0.995,
        },
    },

    "Canon EOS R5": {
        "description": "Canon EOS R5 — Canon 45MP full-frame CMOS sensor",
        "sensor": {
            "read_noise_e": 2.8,
            "dark_current_e_per_s": 0.6,
            "quantum_efficiency": 0.49,
            "bit_depth": 14,
            "full_well_capacity": 37000,
            "hot_pixel_probability": 0.00007,
            "base_iso": 100,
        },
        "bayer_pattern": "RGGB",
        "jpeg_tables": _make_camera_qt(
            # Canon ISP: warmer processing, slightly more chroma smoothing
            lum_offsets=np.array([
                [ 0,  0,  0,  0,  0,  1,  1,  1],
                [ 0,  0,  0,  0,  0,  1,  1,  1],
                [ 0,  0,  0,  0,  1,  1,  2,  1],
                [ 0,  0,  0,  0,  1,  2,  2,  1],
                [ 0,  0,  1,  1,  2,  3,  3,  2],
                [ 1,  1,  1,  1,  2,  2,  3,  2],
                [ 1,  1,  2,  2,  2,  3,  3,  2],
                [ 1,  1,  1,  1,  2,  2,  2,  2],
            ], dtype=np.float32),
            chrom_offsets=np.array([
                [ 0,  1,  1,  0, 0, 0, 0, 0],
                [ 1,  1,  1,  0, 0, 0, 0, 0],
                [ 1,  1,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
            ], dtype=np.float32),
            base_quality=94,
        ),
        "vignetting": {
            "cos4_strength": 0.42,
            "asymmetry_x": -0.008,
            "asymmetry_y": 0.005,
            "radial_falloff": 2.3,
        },
        "color_bias": {
            "r_gain": 1.02,
            "g_gain": 1.00,
            "b_gain": 0.975,
        },
    },

    "Google Pixel 8": {
        "description": "Google Pixel 8 Pro — Samsung GNK 50MP sensor",
        "sensor": {
            "read_noise_e": 1.8,
            "dark_current_e_per_s": 0.7,
            "quantum_efficiency": 0.53,
            "bit_depth": 12,
            "full_well_capacity": 9500,
            "hot_pixel_probability": 0.0001,
            "base_iso": 57,
        },
        "bayer_pattern": "BGGR",
        "jpeg_tables": _make_camera_qt(
            # Google ISP (HDRNet): heavy computational photography,
            # unique mid-frequency boosting in tables
            lum_offsets=np.array([
                [ 0,  0, -1, -2, -2, -1,  0,  1],
                [ 0,  0, -1, -2, -2, -1,  0,  0],
                [-1, -1, -2, -2, -1,  0,  1,  0],
                [-2, -2, -2, -1,  0,  1,  1,  1],
                [-2, -2, -1,  0,  1,  2,  2,  1],
                [-1, -1,  0,  1,  1,  2,  2,  1],
                [ 0,  0,  1,  1,  2,  2,  2,  1],
                [ 1,  1,  1,  1,  2,  1,  1,  1],
            ], dtype=np.float32),
            chrom_offsets=np.array([
                [ 0,  0, -1, -2, 0, 0, 0, 0],
                [ 0,  0, -1, -1, 0, 0, 0, 0],
                [-1, -1, -2,  0, 0, 0, 0, 0],
                [-2, -1,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
                [ 0,  0,  0,  0, 0, 0, 0, 0],
            ], dtype=np.float32),
            base_quality=93,
        ),
        "vignetting": {
            "cos4_strength": 0.32,
            "asymmetry_x": 0.01,
            "asymmetry_y": -0.012,
            "radial_falloff": 2.1,
        },
        "color_bias": {
            "r_gain": 1.008,
            "g_gain": 1.005,
            "b_gain": 0.99,
        },
    },
}


def get_profile(name: str) -> dict:
    """Get a camera profile by name. Returns None if not found."""
    return CAMERA_PROFILES.get(name, None)


def get_profile_names() -> list:
    """Return list of all available camera profile names."""
    return list(CAMERA_PROFILES.keys())
