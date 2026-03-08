"""
Camera Forensic Realism Engine - Core Processing Pipeline v2
Complete rewrite focused on accurate iPhone ISP color science emulation.

Instead of cheap "filter" effects, this implements the actual processing
stages of Apple's Image Signal Processor:

  1. iPhone Tone Mapping (S-curve with highlight rolloff + shadow lift)
  2. Display P3 Color Rendering (wider gamut → natural rich colors)
  3. Smart HDR Local Tone Mapping (adaptive micro-contrast)
  4. Real Tone Skin Rendering (warm, natural skin preservation)
  5. ISP Sharpening (unsharp mask like Apple's ISP)
  6. Subtle Sensor Characteristics (minimal, tasteful noise + vignette)

All processing operates on numpy float32 arrays in [0, 1] range.
"""

import numpy as np
from typing import Optional


# ============================================================================
# UTILITY: Color Space Conversions
# ============================================================================

def _srgb_to_linear(img: np.ndarray) -> np.ndarray:
    """Decode sRGB gamma to linear light (IEC 61966-2-1)."""
    out = np.where(
        img <= 0.04045,
        img / 12.92,
        np.power(np.clip((img + 0.055) / 1.055, 0, None), 2.4)
    )
    return out.astype(np.float32)


def _linear_to_srgb(img: np.ndarray) -> np.ndarray:
    """Encode linear light to sRGB gamma."""
    out = np.where(
        img <= 0.0031308,
        img * 12.92,
        1.055 * np.power(np.clip(img, 0, None), 1.0 / 2.4) - 0.055
    )
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _rgb_to_hsl(img: np.ndarray) -> np.ndarray:
    """Convert RGB [0,1] to HSL [0,1]. Vectorized."""
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    # Lightness
    l = (cmax + cmin) / 2.0

    # Saturation
    s = np.where(delta < 1e-7, 0.0,
                 delta / (1.0 - np.abs(2.0 * l - 1.0) + 1e-7))

    # Hue
    h = np.zeros_like(l)
    mask_r = (cmax == r) & (delta > 1e-7)
    mask_g = (cmax == g) & (delta > 1e-7)
    mask_b = (cmax == b) & (delta > 1e-7)

    h[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6
    h[mask_g] = ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2
    h[mask_b] = ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4
    h = h / 6.0

    return np.stack([h, s, l], axis=-1).astype(np.float32)


def _hsl_to_rgb(hsl: np.ndarray) -> np.ndarray:
    """Convert HSL [0,1] to RGB [0,1]. Vectorized."""
    h, s, l = hsl[:, :, 0], hsl[:, :, 1], hsl[:, :, 2]

    c = (1.0 - np.abs(2.0 * l - 1.0)) * s
    x = c * (1.0 - np.abs((h * 6.0) % 2 - 1.0))
    m = l - c / 2.0

    h6 = h * 6.0
    r = np.zeros_like(h)
    g = np.zeros_like(h)
    b = np.zeros_like(h)

    # Sector 0: [0, 1)
    mask = (h6 >= 0) & (h6 < 1)
    r[mask] = c[mask]; g[mask] = x[mask]
    # Sector 1: [1, 2)
    mask = (h6 >= 1) & (h6 < 2)
    r[mask] = x[mask]; g[mask] = c[mask]
    # Sector 2: [2, 3)
    mask = (h6 >= 2) & (h6 < 3)
    g[mask] = c[mask]; b[mask] = x[mask]
    # Sector 3: [3, 4)
    mask = (h6 >= 3) & (h6 < 4)
    g[mask] = x[mask]; b[mask] = c[mask]
    # Sector 4: [4, 5)
    mask = (h6 >= 4) & (h6 < 5)
    r[mask] = x[mask]; b[mask] = c[mask]
    # Sector 5: [5, 6)
    mask = (h6 >= 5) & (h6 < 6)
    r[mask] = c[mask]; b[mask] = x[mask]

    result = np.stack([r + m, g + m, b + m], axis=-1)
    return np.clip(result, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 1: iPhone Tone Mapping
# ============================================================================

def apply_iphone_tone_curve(image: np.ndarray, strength: float = 0.7,
                             highlight_rolloff: float = 0.6,
                             shadow_lift: float = 0.4,
                             contrast: float = 0.5) -> np.ndarray:
    """Apply Apple-style S-curve tone mapping.

    iPhone ISP characteristics:
    - Smooth highlight compression (prevents clipping, preserves sky detail)
    - Shadow lifting (brightens dark areas for visibility without looking flat)
    - Mid-tone contrast boost (punchy but not harsh)
    - Filmic rolloff in highlights (smooth transition to white)

    All adjustable. The defaults emulate the iPhone 15 Pro "Standard" style.
    """
    if strength <= 0:
        return image

    # Work in linear light for physically correct processing
    linear = _srgb_to_linear(image)

    # --- S-Curve via rational function (smoother than sigmoid) ---
    # This approximates Apple's proprietary tone curve:
    # - Lifts shadows gently (iPhone never crushes blacks)
    # - Boosts mid-tones for "punchy" look
    # - Rolls off highlights smoothly (filmic, not digital clip)

    # Shadow lift: raise the floor of the curve
    shadow_offset = shadow_lift * 0.03 * strength
    linear = linear + shadow_offset

    # Contrast S-curve using a smooth power function
    # Pivot around mid-gray (0.18 in linear = middle gray)
    pivot = 0.18
    contrast_amount = 1.0 + contrast * 0.6 * strength

    # Apply per-channel contrast around pivot
    result = pivot * np.power(linear / (pivot + 1e-6), contrast_amount)

    # Highlight rolloff: compress highlights smoothly
    # Uses a soft-knee compression curve
    knee = 1.0 - highlight_rolloff * 0.3 * strength
    above_knee = result > knee
    if np.any(above_knee):
        excess = result[above_knee] - knee
        # Soft compression: maps excess through a log curve
        compressed = knee + (1.0 - knee) * (1.0 - np.exp(-excess / ((1.0 - knee) + 1e-6)))
        result[above_knee] = compressed

    # Convert back to sRGB
    result = _linear_to_srgb(np.clip(result, 0.0, 1.0))

    # Blend with original
    output = image * (1.0 - strength) + result * strength
    return np.clip(output, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 2: Display P3 Color Rendering
# ============================================================================

# Transform matrices (CIE XYZ as intermediate)
# sRGB -> XYZ (D65)
_SRGB_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
], dtype=np.float32)

# XYZ -> Display P3 (D65)
_XYZ_TO_P3 = np.array([
    [ 2.4934969, -0.9313836, -0.4027108],
    [-0.8294890,  1.7626641,  0.0236247],
    [ 0.0358458, -0.0761724,  0.9568845],
], dtype=np.float32)

# Display P3 -> XYZ (D65)
_P3_TO_XYZ = np.array([
    [0.4865709, 0.2656677, 0.1982173],
    [0.2289746, 0.6917385, 0.0792869],
    [0.0000000, 0.0451134, 1.0439444],
], dtype=np.float32)

# XYZ -> sRGB (D65)
_XYZ_TO_SRGB = np.array([
    [ 3.2404542, -1.5371385, -0.4985314],
    [-0.9692660,  1.8760108,  0.0415560],
    [ 0.0556434, -0.2040259,  1.0572252],
], dtype=np.float32)


def apply_p3_color_rendering(image: np.ndarray, strength: float = 0.5,
                              saturation_boost: float = 0.3,
                              warmth: float = 0.3) -> np.ndarray:
    """Simulate iPhone's Display P3 wider gamut color rendering.

    iPhones capture and display in Display P3, which has ~25% more colors
    than sRGB, especially in reds and greens. This makes photos look
    richer and more vibrant without being garish.

    This stage:
    1. Converts to linear light
    2. Transforms from sRGB gamut to P3 gamut (expanding color range)
    3. Applies subtle saturation and warmth adjustments
    4. Converts back to sRGB with soft gamut clipping

    The result: richer reds, deeper greens, more vibrant skin tones —
    the signature "iPhone color pop" without oversaturation.
    """
    if strength <= 0:
        return image

    # Convert to linear
    linear = _srgb_to_linear(image)

    h, w, _ = linear.shape
    pixels = linear.reshape(-1, 3)

    # sRGB -> XYZ -> P3
    xyz = (pixels @ _SRGB_TO_XYZ.T)
    p3 = (xyz @ _XYZ_TO_P3.T)

    # In P3 space, apply subtle saturation boost
    # (This simulates the wider gamut's richer color reproduction)
    p3_mean = p3.mean(axis=1, keepdims=True)
    sat_factor = 1.0 + saturation_boost * 0.8 * strength
    p3_saturated = p3_mean + (p3 - p3_mean) * sat_factor

    # Apply warmth shift (iPhone's warm bias)
    # Slightly boost red, slightly reduce blue
    warmth_factor = warmth * strength
    p3_saturated[:, 0] *= (1.0 + 0.15 * warmth_factor)  # Red warmer
    p3_saturated[:, 1] *= (1.0 + 0.04 * warmth_factor)  # Green slight warm
    p3_saturated[:, 2] *= (1.0 - 0.12 * warmth_factor)  # Blue cooler

    # P3 -> XYZ -> sRGB (with soft gamut clipping)
    xyz_back = (p3_saturated @ _P3_TO_XYZ.T)
    srgb_linear = (xyz_back @ _XYZ_TO_SRGB.T)

    # Soft gamut clip: instead of hard [0,1] clip, use smooth compression
    # This prevents color shifts at gamut boundaries
    srgb_linear = np.clip(srgb_linear, 0, None)
    over_mask = srgb_linear > 1.0
    if np.any(over_mask):
        excess = srgb_linear[over_mask] - 1.0
        srgb_linear[over_mask] = 1.0 - np.exp(-excess) * 0.05

    srgb_linear = np.clip(srgb_linear, 0.0, 1.0).reshape(h, w, 3)

    # Back to sRGB gamma
    result = _linear_to_srgb(srgb_linear)

    output = image * (1.0 - strength) + result * strength
    return np.clip(output, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 3: Smart HDR Local Tone Mapping
# ============================================================================

def _box_blur(img: np.ndarray, radius: int) -> np.ndarray:
    """Fast box blur using cumulative sum. Works on 2D arrays."""
    if radius <= 0:
        return img
    # Horizontal pass
    cs = np.cumsum(img, axis=1)
    cs = np.pad(cs, ((0, 0), (radius, 0)), mode='constant')
    blurred = (cs[:, radius:] - cs[:, :-radius]) / radius

    # Vertical pass
    cs = np.cumsum(blurred, axis=0)
    cs = np.pad(cs, ((radius, 0), (0, 0)), mode='constant')
    blurred = (cs[radius:, :] - cs[:-radius, :]) / radius

    # Handle shape mismatch from integer division
    h, w = img.shape
    blurred = blurred[:h, :w]
    return blurred.astype(np.float32)


def apply_local_tone_mapping(image: np.ndarray, strength: float = 0.4,
                              detail_boost: float = 0.5,
                              radius_pct: float = 0.08) -> np.ndarray:
    """Apply Smart HDR-inspired local tone mapping.

    Apple's Smart HDR captures multiple exposures and fuses them.
    We simulate the visual result:
    - Local contrast enhancement (makes textures pop)
    - Brings out detail in both shadows and highlights
    - Creates that "HDR but natural" iPhone look
    - Adds micro-contrast that makes the image feel sharp and alive

    Uses a fast approximation of unsharp-mask local tone mapping.
    """
    if strength <= 0:
        return image

    h, w = image.shape[:2]
    radius = max(3, int(min(h, w) * radius_pct))

    # Convert to luminance for local adaptation
    lum = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]

    # Compute local mean luminance (what Smart HDR adapts to)
    local_mean = _box_blur(lum, radius)

    # Local detail = difference between pixel and local average
    # This is the micro-contrast/texture information
    detail = lum - local_mean

    # Enhance detail (boost local contrast)
    detail_factor = 1.0 + detail_boost * strength * 2.5
    enhanced_detail = detail * detail_factor

    # Build luminance correction map
    # Where local_mean is dark -> lighten (shadow lift)
    # Where local_mean is bright -> darken slightly (highlight recovery)
    target_mean = 0.5  # Compress toward middle gray
    correction = (target_mean - local_mean) * 0.7 * strength

    # Apply luminance correction per channel (preserves color ratios)
    lum_ratio = np.clip(lum, 1e-6, None)

    # New luminance = corrected local mean + enhanced detail
    new_lum = local_mean + correction + enhanced_detail
    new_lum = np.clip(new_lum, 0.0, 1.0)

    # Scale RGB channels by luminance change ratio
    scale = (new_lum / lum_ratio)[:, :, np.newaxis]
    scale = np.clip(scale, 0.5, 2.0)  # Prevent extreme scaling

    result = image * scale

    # Blend with original
    output = image * (1.0 - strength) + result * strength
    return np.clip(output, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 4: Real Tone Skin Rendering
# ============================================================================

def apply_skin_tone_rendering(image: np.ndarray, strength: float = 0.5,
                               warmth: float = 0.5,
                               smoothness: float = 0.3) -> np.ndarray:
    """Apply Apple's Real Tone skin rendering.

    Apple specifically optimizes skin tone reproduction:
    - Detects skin-tone hue ranges (orange-ish, 15-45 degree hue)
    - Applies warmth while preventing oversaturation
    - Slightly reduces chroma in very saturated skin to prevent "orange look"
    - Preserves natural variation across skin tones

    This works in HSL space for precise skin tone targeting.
    """
    if strength <= 0:
        return image

    hsl = _rgb_to_hsl(image)
    h, s, l = hsl[:, :, 0], hsl[:, :, 1], hsl[:, :, 2]

    # Skin tone detection mask (hue range ~15-50 degrees = 0.04-0.14 in [0,1])
    # with saturation > 0.15 and luminance in reasonable range
    skin_hue_center = 0.08  # ~30 degrees (warm skin tone center)
    skin_hue_width = 0.12   # ~43 degrees on each side

    hue_dist = np.minimum(np.abs(h - skin_hue_center),
                          np.abs(h - skin_hue_center + 1.0))
    hue_dist = np.minimum(hue_dist, np.abs(h - skin_hue_center - 1.0))

    # Smooth falloff skin mask (0 = not skin, 1 = definitely skin)
    skin_mask = np.exp(-0.5 * (hue_dist / (skin_hue_width + 1e-6)) ** 2)
    skin_mask *= np.clip(s * 4.0, 0, 1)  # Need some saturation
    skin_mask *= np.clip(1.0 - np.abs(l - 0.5) * 3.0, 0, 1)  # Not too dark/bright
    skin_mask = skin_mask.astype(np.float32)

    # Apply effects ONLY to skin regions
    effect_strength = skin_mask * strength

    # 1. Warmth: shift skin hue slightly toward warm (lower hue = more red-orange)
    h_shift = -0.06 * warmth  # Subtle warmth push
    h_new = h + h_shift * effect_strength

    # 2. Saturation control: prevent oversaturated orange skin
    # Reduce saturation for overly-saturated skin tones
    s_target = np.clip(s, 0, 0.45)  # iPhone caps skin saturation to prevent "orange face"
    s_new = s + (s_target - s) * effect_strength * 0.7

    # 3. Luminance: slight brighten for skin (Real Tone lifts skin slightly)
    l_boost = 0.12 * strength
    l_new = l + l_boost * effect_strength

    # Recombine
    hsl_new = np.stack([h_new % 1.0, np.clip(s_new, 0, 1),
                        np.clip(l_new, 0, 1)], axis=-1).astype(np.float32)
    result = _hsl_to_rgb(hsl_new)

    return np.clip(result, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 5: Deep Fusion Texture Crunch (Edge-Preserving Frequency Separation)
# ============================================================================

def apply_deep_fusion_crunch(image: np.ndarray, strength: float = 0.5,
                             texture_frequency: float = 0.5) -> np.ndarray:
    """Simulate Apple's Deep Fusion algorithm.
    
    Rather than a basic unsharp mask which creates halos around high-contrast 
    edges (like a tree against a sky) and amplifies noise in flat areas, 
    Deep Fusion isolates mid-to-high frequency *textures* (fabric, skin pores)
    and massively amplifies them, using an edge-preserving variance mask.
    """
    if strength <= 0:
        return image
        
    h, w = image.shape[:2]
    
    # Extract luminance
    lum = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]
    
    # 1. Fast Edge-Preserving Low-Pass Filter (Guided/Bilateral Approximation)
    # We compute local variance to identify hard edges vs textures vs flat areas.
    radius = max(2, int(min(h, w) * 0.015 * texture_frequency)) # Base structure radius
    
    # E[X] and E[X^2] for variance
    mean_lum = _box_blur(lum, radius)
    mean_lum_sq = _box_blur(lum * lum, radius)
    
    # Local Variance: V(X) = E[X^2] - (E[X])^2
    var_lum = np.clip(mean_lum_sq - mean_lum * mean_lum, 0.0, None)
    
    # Scale variance to use as a mask
    # Flat areas have var ~0. Hard edges have high var. 
    # Textures exist in the middle variance band.
    edge_threshold = 0.05
    edge_mask = np.clip(var_lum / edge_threshold, 0.0, 1.0)
    
    # The detail layer (high frequencies)
    detail = lum - mean_lum
    
    # We want to amplify details where it is NOT a hard edge (where edge_mask is low)
    # but we also don't want to amplify pure flat noise. 
    # So we enhance based on an inverse edge mask.
    texture_mask = 1.0 - edge_mask
    
    # Deep Fusion is aggressive. At max strength we're multiplying texture by 3x.
    crunch_factor = strength * 2.5
    amplified_detail = detail * (1.0 + crunch_factor * texture_mask)
    
    # Recombine luminance
    new_lum = mean_lum + amplified_detail
    new_lum = np.clip(new_lum, 0.0, 1.0)
    
    # Scale RGB by luminance ratio
    lum_safe = np.clip(lum, 1e-6, None)
    scale = (new_lum / lum_safe)[:, :, np.newaxis]
    scale = np.clip(scale, 0.5, 2.0)
    
    result = image * scale
    return np.clip(result, 0.0, 1.0).astype(np.float32)

# ============================================================================
# STAGE 6: ISP Sharpening (Unsharp Mask)
# ============================================================================

def apply_isp_sharpening(image: np.ndarray, strength: float = 0.3,
                          radius_pct: float = 0.005) -> np.ndarray:
    """Apply iPhone ISP-style unsharp masking.

    Apple's ISP applies subtle, intelligent sharpening:
    - Operates primarily on luminance (avoids color artifacts)
    - Small radius (captures fine detail like skin pores, hair)
    - Moderate strength (visible but not crunchy)
    - Slightly halos permitted (signature iPhone "crispness")
    """
    if strength <= 0:
        return image

    h, w = image.shape[:2]
    radius = max(1, int(min(h, w) * radius_pct))

    # Extract luminance
    lum = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]

    # Blur for unsharp mask
    blurred = _box_blur(lum, radius)

    # High-frequency detail
    detail = lum - blurred

    # Apply sharpening via luminance scaling
    sharp_amount = strength * 1.5
    sharpened_lum = lum + detail * sharp_amount
    sharpened_lum = np.clip(sharpened_lum, 0.0, 1.0)

    # Scale RGB channels by luminance change
    lum_safe = np.clip(lum, 1e-6, None)
    scale = (sharpened_lum / lum_safe)[:, :, np.newaxis]
    scale = np.clip(scale, 0.7, 1.5)  # Prevent extreme scaling

    result = image * scale

    return np.clip(result, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 7: Subtle Sensor Characteristics
# ============================================================================

def apply_sensor_character(image: np.ndarray, strength: float = 0.3,
                            noise_amount: float = 0.3,
                            vignette_amount: float = 0.4,
                            seed: int = 42) -> np.ndarray:
    """Apply subtle real-camera sensor characteristics.

    Minimal, tasteful, not a filter:
    - Very subtle luminance-only noise (like iPhone at ISO 200-400)
    - Gentle vignette matching iPhone's f/1.78 lens
    - Not the main effect — just finishing touches
    """
    if strength <= 0:
        return image

    h, w = image.shape[:2]
    result = image.copy()
    rng = np.random.default_rng(seed)

    # --- Subtle luminance noise (iPhone-like, barely visible) ---
    if noise_amount > 0:
        # iPhone noise is very fine-grained, mostly in shadows
        lum = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]

        # More noise in shadows, less in highlights (like real sensors)
        noise_scale = (1.0 - lum) * 0.015 * noise_amount * strength
        noise = rng.normal(0, 1, (h, w)).astype(np.float32) * noise_scale

        # Apply noise to all channels equally (luminance-style noise)
        result = result + noise[:, :, np.newaxis]

    # --- Gentle vignette (iPhone f/1.78 lens) ---
    if vignette_amount > 0:
        y = np.linspace(-1, 1, h, dtype=np.float32)
        x = np.linspace(-1, 1, w, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)
        r = np.sqrt(xx ** 2 + yy ** 2)
        r_norm = r / np.sqrt(2.0)

        # iPhone vignette is very gentle, almost imperceptible
        vig = 1.0 - vignette_amount * 0.12 * strength * np.power(r_norm, 2.5)
        vig = np.clip(vig, 0.0, 1.0).astype(np.float32)
        result = result * vig[:, :, np.newaxis]

    return np.clip(result, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 8: Color Temperature & White Balance
# ============================================================================

def apply_white_balance(image: np.ndarray, strength: float = 0.5,
                         temperature: float = 0.3,
                         tint: float = 0.0) -> np.ndarray:
    """Apply iPhone-style automatic white balance correction.

    iPhone AWB tends toward:
    - Slightly warm (daylight bias)
    - Neutral tint (no green/magenta shift)
    - Accurate gray point targeting

    Temperature: -1 (cool/blue) to +1 (warm/orange). Default 0.3 = iPhone warm.
    Tint: -1 (green) to +1 (magenta). Default 0 = neutral.
    """
    if strength <= 0:
        return image

    result = image.copy()

    # Temperature: warm = boost red/yellow, cool = boost blue
    temp_effect = temperature * 0.25 * strength
    result[:, :, 0] = result[:, :, 0] * (1.0 + temp_effect * 1.0)   # Red
    result[:, :, 1] = result[:, :, 1] * (1.0 + temp_effect * 0.3)   # Green (slight)
    result[:, :, 2] = result[:, :, 2] * (1.0 - temp_effect * 0.8)   # Blue

    # Tint: green-magenta axis
    tint_effect = tint * 0.2 * strength
    result[:, :, 1] = result[:, :, 1] * (1.0 + tint_effect)  # Green

    return np.clip(result, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 9: iPhone Blue Shadow Tint (HDR Artifact)
# ============================================================================

def apply_blue_shadow_tint(image: np.ndarray, strength: float = 0.4,
                            shadow_threshold: float = 0.35,
                            blue_intensity: float = 0.5) -> np.ndarray:
    """Apply iPhone's characteristic blue-ish tint in dark areas.

    iPhones are known for lifting shadows with a subtle blue/purple cast.
    This comes from HDR processing: when the ISP lifts shadow detail,
    it shifts the blacks toward blue instead of pure neutral.

    This is a very recognizable iPhone trait — dark clothes, hair, and
    shadows all have this subtle blue tint in iPhone photos.

    Uses luminance-based masking with smooth cubic falloff so only
    genuinely dark areas receive the tint.
    """
    if strength <= 0:
        return image

    # Compute luminance
    lum = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]

    # Shadow mask: 1.0 in deepest shadows, smooth falloff to 0.0
    # Uses cubic falloff for natural transition
    shadow_mask = np.clip((shadow_threshold - lum) / (shadow_threshold + 1e-6), 0.0, 1.0)
    shadow_mask = shadow_mask ** 2  # Smooth cubic-like falloff
    shadow_mask = (shadow_mask * strength)[:, :, np.newaxis].astype(np.float32)

    # Blue tint color shift:
    # Slightly reduce red + green in shadows, boost blue
    # This creates that characteristic iPhone blue-black look
    tint = np.zeros_like(image)
    tint[:, :, 0] = -0.15 * blue_intensity  # Reduce red in shadows
    tint[:, :, 1] = -0.05 * blue_intensity  # Slightly reduce green
    tint[:, :, 2] = +0.25 * blue_intensity  # Boost blue in shadows

    result = image + tint * shadow_mask

    return np.clip(result, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 10: Highlight Warmth (iPhone golden highlights)
# ============================================================================

def apply_highlight_warmth(image: np.ndarray, strength: float = 0.3,
                            highlight_threshold: float = 0.7,
                            warmth: float = 0.5) -> np.ndarray:
    """Apply warm golden tint to highlights (iPhone characteristic).

    iPhone photos have subtly warm highlights — sunlit areas, bright skin,
    and light sources all have a gentle golden quality. This complements
    the blue shadows to create the full iPhone color signature:
    warm highlights + cool/blue shadows = the iPhone look.
    """
    if strength <= 0:
        return image

    lum = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]

    # Highlight mask: smooth ramp in bright areas
    hl_mask = np.clip((lum - highlight_threshold) / (1.0 - highlight_threshold + 1e-6), 0.0, 1.0)
    hl_mask = (hl_mask * strength)[:, :, np.newaxis].astype(np.float32)

    # Golden warmth: boost red/yellow in highlights
    tint = np.zeros_like(image)
    tint[:, :, 0] = +0.18 * warmth   # Warm red
    tint[:, :, 1] = +0.06 * warmth   # Slight green-yellow
    tint[:, :, 2] = -0.12 * warmth   # Reduce blue in highlights

    result = image + tint * hl_mask
    return np.clip(result, 0.0, 1.0).astype(np.float32)


# ============================================================================
# MASTER PIPELINE
# ============================================================================

def process_iphone_realism(image: np.ndarray,
                            master_strength: float = 0.7,
                            # Tone mapping
                            enable_tone_mapping: bool = True,
                            tone_strength: float = 0.6,
                            highlight_rolloff: float = 0.5,
                            shadow_lift: float = 0.4,
                            contrast: float = 0.5,
                            # P3 Color
                            enable_p3_color: bool = True,
                            color_strength: float = 0.5,
                            color_saturation: float = 0.3,
                            color_warmth: float = 0.3,
                            # Local tone mapping
                            enable_local_tone: bool = True,
                            local_tone_strength: float = 0.35,
                            detail_boost: float = 0.4,
                            # Skin rendering
                            enable_skin_rendering: bool = True,
                            skin_strength: float = 0.5,
                            skin_warmth: float = 0.4,
                            # Deep Fusion Texture Crunch
                            enable_deep_fusion: bool = True,
                            fusion_strength: float = 0.6,
                            fusion_texture_freq: float = 0.5,
                            # White balance
                            enable_white_balance: bool = True,
                            wb_strength: float = 0.5,
                            wb_temperature: float = 0.25,
                            wb_tint: float = 0.0,
                            # Color grading (blue shadows + warm highlights)
                            enable_color_grading: bool = True,
                            blue_shadows: float = 0.4,
                            warm_highlights: float = 0.3,
                            # Sharpening
                            enable_sharpening: bool = True,
                            sharpen_strength: float = 0.3,
                            # Sensor characteristics
                            enable_sensor: bool = True,
                            sensor_strength: float = 0.25,
                            sensor_noise: float = 0.3,
                            sensor_vignette: float = 0.4,
                            seed: int = 42) -> np.ndarray:
    """Run the full iPhone ISP Realism pipeline.

    Processing order matches Apple's actual ISP pipeline:
    1. White balance correction (first in real ISP)
    2. Tone mapping (exposure + S-curve)
    3. Display P3 color rendering (gamut + color science)
    4. Smart HDR local tone mapping (multi-frame fusion emulation)
    5. Real Tone skin rendering (skin-specific optimization)
    6. Deep Fusion texture crunch (edge-preserving high-frequency boost)
    7. Color grading (blue shadows + warm highlights)
    8. ISP sharpening (crispness)
    9. Sensor characteristics (subtle noise + vignette)
    """
    result = image.copy()

    # Stage 1: White Balance
    if enable_white_balance:
        result = apply_white_balance(result, wb_strength * master_strength,
                                      wb_temperature, wb_tint)

    # Stage 2: Tone Mapping
    if enable_tone_mapping:
        result = apply_iphone_tone_curve(result, tone_strength * master_strength,
                                          highlight_rolloff, shadow_lift, contrast)

    # Stage 3: P3 Color Rendering
    if enable_p3_color:
        result = apply_p3_color_rendering(result, color_strength * master_strength,
                                           color_saturation, color_warmth)

    # Stage 4: Local Tone Mapping
    if enable_local_tone:
        result = apply_local_tone_mapping(result, local_tone_strength * master_strength,
                                           detail_boost)

    # Stage 5: Skin Rendering
    if enable_skin_rendering:
        result = apply_skin_tone_rendering(result, skin_strength * master_strength,
                                            skin_warmth)

    # Stage 6: Deep Fusion Texture Crunch
    if enable_deep_fusion:
        result = apply_deep_fusion_crunch(result, fusion_strength * master_strength, fusion_texture_freq)

    # Stage 7: Color Grading (iPhone signature: blue shadows + warm highlights)
    if enable_color_grading:
        result = apply_blue_shadow_tint(result, blue_shadows * master_strength)
        result = apply_highlight_warmth(result, warm_highlights * master_strength)

    # Stage 8: Sharpening
    if enable_sharpening:
        result = apply_isp_sharpening(result, sharpen_strength * master_strength)

    # Stage 9: Sensor Character
    if enable_sensor:
        result = apply_sensor_character(result, sensor_strength * master_strength,
                                         sensor_noise, sensor_vignette, seed)

    return np.clip(result, 0.0, 1.0).astype(np.float32)
