"""
Camera Forensic Realism Engine — Core Processing Pipeline v4
iPhone 17 ISP color science emulation.

Honest, physically-grounded processing. Every stage does real work:

  1. White Balance      — channel gains in LINEAR light, luminance-preserving
  2. Global Tone        — exposure, shadow gain, midtone contrast around the
                          0.18 photographic pivot, Reinhard highlight rolloff
  3. Smart HDR (local)  — Durand-style log-luminance base/detail separation;
                          compresses the base layer, keeps detail intact
  4. Color Science      — performed in Oklab (perceptually uniform):
                          hue-preserving vibrance, genuine skin-tone
                          protection, subtle iPhone split-tone
                          (cool shadows / warm highlights)
  5. Detail             — single two-scale (texture + clarity) luminance
                          unsharp with tanh halo suppression
  6. Optics & Sensor    — natural-falloff vignette (linear light) and
                          photon-weighted luminance grain

Plus iPhone 17 Photographic Styles presets (undertones + moods) applied
as parameter offsets on top of the user's slider values.

All processing operates on numpy float32 arrays in [0, 1] range.
"""

import numpy as np


# ============================================================================
# Color transforms
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


# Oklab (Björn Ottosson) — perceptually uniform, hue-linear.
# Vibrance/skin/split-tone math in Oklab does not produce the hue shifts
# that naive RGB saturation does.
_LIN_SRGB_TO_LMS = np.array([
    [0.4122214708, 0.5363325363, 0.0514459929],
    [0.2119034982, 0.6806995451, 0.1073969566],
    [0.0883024619, 0.2817188376, 0.6299787005],
], dtype=np.float32)

_LMS_TO_OKLAB = np.array([
    [0.2104542553, 0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050, 0.4505937099],
    [0.0259040371, 0.7827717662, -0.8086757660],
], dtype=np.float32)

_OKLAB_TO_LMS = np.array([
    [1.0, 0.3963377774, 0.2158037573],
    [1.0, -0.1055613458, -0.0638541728],
    [1.0, -0.0894841775, -1.2914855480],
], dtype=np.float32)

_LMS_TO_LIN_SRGB = np.array([
    [4.0767416621, -3.3077115913, 0.2309699292],
    [-1.2684380046, 2.6097574011, -0.3413193965],
    [-0.0041960863, -0.7034186147, 1.7076147010],
], dtype=np.float32)


def _linear_rgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    lms = rgb @ _LIN_SRGB_TO_LMS.T
    lms = np.cbrt(lms)
    return (lms @ _LMS_TO_OKLAB.T).astype(np.float32)


def _oklab_to_linear_rgb(lab: np.ndarray) -> np.ndarray:
    lms = lab @ _OKLAB_TO_LMS.T
    lms = lms * lms * lms
    return (lms @ _LMS_TO_LIN_SRGB.T).astype(np.float32)


_LUMA_W = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def _luma(img: np.ndarray) -> np.ndarray:
    """Rec.709 luminance of an (H, W, 3) array."""
    return (img @ _LUMA_W).astype(np.float32)


# ============================================================================
# Centered box blur (correct — the old version was a trailing window that
# shifted the image diagonally and averaged zeros in at the borders)
# ============================================================================

def _box_blur(img: np.ndarray, radius: int) -> np.ndarray:
    """Centered box blur of a 2D array with edge-replicate padding."""
    if radius < 1:
        return img.astype(np.float32)
    k = 2 * radius + 1

    # Vertical pass
    p = np.pad(img, ((radius, radius), (0, 0)), mode='edge')
    cs = np.cumsum(p, axis=0, dtype=np.float64)
    cs = np.vstack([np.zeros((1, cs.shape[1]), dtype=np.float64), cs])
    out = (cs[k:, :] - cs[:-k, :]) / k

    # Horizontal pass
    p = np.pad(out, ((0, 0), (radius, radius)), mode='edge')
    cs = np.cumsum(p, axis=1, dtype=np.float64)
    cs = np.hstack([np.zeros((cs.shape[0], 1), dtype=np.float64), cs])
    out = (cs[:, k:] - cs[:, :-k]) / k

    return out.astype(np.float32)


def _smooth(img: np.ndarray, radius: int) -> np.ndarray:
    """Two box passes ≈ triangle filter (smoother halos than a single box)."""
    return _box_blur(_box_blur(img, radius), radius)


def _smoothstep01(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


# ============================================================================
# iPhone 17 Photographic Styles
# ============================================================================
# Offsets added to the user's slider values, then clamped to valid range.
# Undertone styles steer white balance / warmth; mood styles steer tone
# and color rendering — mirroring Apple's 2nd-gen Photographic Styles.

PHOTOGRAPHIC_STYLES = {
    # --- baseline ---
    "Standard":   {},
    # --- mood styles ---
    "Natural":    {"vibrance": -0.18, "contrast": -0.10, "shadow_tint": -0.15,
                   "highlight_warmth": -0.08, "clarity": -0.08},
    "Luminous":   {"exposure": +0.18, "shadows": +0.15, "contrast": -0.08,
                   "wb_temperature": +0.05, "vibrance": +0.05},
    "Vibrant":    {"vibrance": +0.28, "contrast": +0.10, "clarity": +0.08},
    "Dramatic":   {"contrast": +0.30, "shadows": -0.20, "exposure": -0.08,
                   "vibrance": -0.05, "clarity": +0.10},
    "Quiet":      {"contrast": -0.18, "vibrance": -0.22, "shadows": +0.12,
                   "wb_temperature": +0.05, "texture": -0.10},
    "Cozy":       {"wb_temperature": +0.20, "highlight_warmth": +0.12,
                   "contrast": -0.06, "vibrance": +0.04},
    "Ethereal":   {"exposure": +0.22, "contrast": -0.22, "vibrance": -0.10,
                   "wb_temperature": -0.05, "shadows": +0.15},
    "Muted B&W":  {"contrast": -0.10, "shadows": +0.12, "grain": +0.10,
                   "_mono": True},
    "Stark B&W":  {"contrast": +0.35, "shadows": -0.10, "grain": +0.05,
                   "_mono": True},
    # --- undertone styles ---
    "Amber":      {"wb_temperature": +0.16, "wb_tint": -0.04,
                   "highlight_warmth": +0.06},
    "Gold":       {"wb_temperature": +0.10, "highlight_warmth": +0.10,
                   "vibrance": +0.04},
    "Rose Gold":  {"wb_temperature": +0.08, "wb_tint": +0.10},
    "Cool Rose":  {"wb_temperature": -0.10, "wb_tint": +0.10},
    "Neutral":    {"wb_temperature": -0.12, "highlight_warmth": -0.10,
                   "shadow_tint": -0.10},
}

_PARAM_BOUNDS = {
    "wb_temperature":   (-1.0, 1.0),
    "wb_tint":          (-1.0, 1.0),
    "exposure":         (-1.0, 1.0),
    "contrast":         (-1.0, 1.0),
    "shadows":          (0.0, 1.0),
    "highlights":       (0.0, 1.0),
    "hdr_strength":     (0.0, 1.0),
    "vibrance":         (0.0, 1.0),
    "skin_protection":  (0.0, 1.0),
    "shadow_tint":      (0.0, 1.0),
    "highlight_warmth": (0.0, 1.0),
    "texture":          (0.0, 1.0),
    "clarity":          (0.0, 1.0),
    "grain":            (0.0, 1.0),
    "vignette":         (0.0, 1.0),
}


def resolve_style(style: str, params: dict) -> dict:
    """Apply a Photographic Style's offsets to the user parameters."""
    out = dict(params)
    out["_mono"] = False
    offsets = PHOTOGRAPHIC_STYLES.get(style, {})
    for key, off in offsets.items():
        if key == "_mono":
            out["_mono"] = True
            continue
        lo, hi = _PARAM_BOUNDS[key]
        out[key] = float(np.clip(out[key] + off, lo, hi))
    return out


# ============================================================================
# STAGE 1: White Balance (linear light)
# ============================================================================

def apply_white_balance(linear: np.ndarray, temperature: float,
                        tint: float) -> np.ndarray:
    """Channel gains in linear light, normalized to preserve luminance.

    temperature: -1 (cool/blue) .. +1 (warm/orange)
    tint:        -1 (green)     .. +1 (magenta)

    Normalizing the gains against Rec.709 luminance weights means warming
    the image does not also brighten it — only the color shifts.
    """
    if temperature == 0.0 and tint == 0.0:
        return linear

    r = (1.0 + 0.30 * temperature) * (1.0 + 0.04 * tint)
    g = 1.0 - 0.12 * tint
    b = (1.0 - 0.25 * temperature) * (1.0 + 0.04 * tint)

    gains = np.array([r, g, b], dtype=np.float32)
    gains /= float((gains * _LUMA_W).sum())
    return (linear * gains).astype(np.float32)


# ============================================================================
# STAGE 2: Global Tone (linear light)
# ============================================================================

def apply_global_tone(linear: np.ndarray, exposure: float, contrast: float,
                      shadows: float, highlights: float) -> np.ndarray:
    """iPhone-style global tone: exposure, shadow gain, midtone contrast,
    Reinhard highlight rolloff. All in linear light.

    exposure:   -1..+1 EV
    contrast:   -1..+1, power curve around the 0.18 middle-gray pivot
    shadows:    0..1, luminance-masked multiplicative lift (no gray haze)
    highlights: 0..1, soft-knee compression (smooth, monotonic — never clips)
    """
    x = linear * np.float32(2.0 ** exposure)

    # Shadow lift: gain that decays with luminance. Multiplicative, so
    # black stays black and there's no hazy pedestal in linear light.
    if shadows > 0.0:
        y = _luma(x)
        gain = 1.0 + 0.9 * shadows * np.exp(-y / 0.08)
        x = x * gain[:, :, np.newaxis]

    # Midtone contrast around photographic middle gray
    if contrast != 0.0:
        c = np.float32(1.0 + 0.55 * contrast)
        x = 0.18 * np.power(np.maximum(x, 0.0) / 0.18, c)

    # Highlight rolloff: Reinhard soft knee above k. Monotonic and smooth,
    # asymptotically approaches 1.0 — the filmic "never blows out" behavior.
    if highlights > 0.0:
        k = np.float32(1.0 - 0.55 * highlights)
        t = np.maximum(x - k, 0.0) / (1.0 - k + 1e-6)
        x = np.where(x > k, k + (1.0 - k) * (t / (1.0 + t)), x)

    return x.astype(np.float32)


# ============================================================================
# STAGE 3: Smart HDR — local tone mapping (log-luminance domain)
# ============================================================================

def apply_smart_hdr(linear: np.ndarray, strength: float) -> np.ndarray:
    """Durand-style local tone mapping on log2 luminance.

    Splits log-luminance into a base layer (large-radius blur) and a detail
    layer. The base is compressed around its own mean — local shadows come
    up, local highlights come down — while detail passes through untouched.
    No gray-wash, no detail loss; this is how multi-frame HDR fusion looks.
    """
    if strength <= 0.0:
        return linear

    h, w = linear.shape[:2]
    y = np.maximum(_luma(linear), 1e-6)
    log_y = np.log2(y)

    radius = max(4, int(min(h, w) * 0.05))
    base = _smooth(log_y, radius)
    detail = log_y - base

    mean = np.float32(base.mean())
    compression = np.float32(1.0 - 0.45 * strength)
    new_log_y = mean + (base - mean) * compression + detail

    ratio = np.exp2(new_log_y) / y
    ratio = np.clip(ratio, 0.35, 2.8)[:, :, np.newaxis]
    return (linear * ratio).astype(np.float32)


# ============================================================================
# STAGE 4: Color Science (Oklab)
# ============================================================================

def apply_color_science(linear: np.ndarray, vibrance: float,
                        skin_protection: float, shadow_tint: float,
                        highlight_warmth: float,
                        mono: bool = False) -> np.ndarray:
    """The actual color rendering, in Oklab.

    - Vibrance: boosts chroma with falloff for already-saturated colors.
      Hue-preserving by construction (chroma scaling in Oklab).
    - Skin protection: a real skin mask (Oklab hue ≈ 50°, plausible chroma
      and lightness) attenuates the vibrance boost on skin and soft-caps
      skin chroma so faces never go orange. Only affects skin pixels.
    - Split tone: iPhone signature — slightly cool shadows, warm highlights.
      Applied as small a/b offsets weighted by lightness masks.
    - mono: Photographic Style B&W rendering (chroma to zero).
    """
    if not mono and vibrance <= 0.0 and shadow_tint <= 0.0 \
            and highlight_warmth <= 0.0:
        return linear

    lab = _linear_rgb_to_oklab(np.maximum(linear, 0.0))
    L = lab[:, :, 0]
    a = lab[:, :, 1]
    b = lab[:, :, 2]

    if mono:
        a = np.zeros_like(a)
        b = np.zeros_like(b)
    else:
        chroma = np.hypot(a, b)
        hue_deg = np.degrees(np.arctan2(b, a))

        # Skin mask: hue near 50° with plausible chroma and lightness
        hue_w = np.exp(-0.5 * ((hue_deg - 50.0) / 18.0) ** 2)
        chroma_w = np.clip(chroma / 0.03, 0.0, 1.0) \
            * np.clip((0.22 - chroma) / 0.08, 0.0, 1.0)
        light_w = np.clip((L - 0.20) / 0.15, 0.0, 1.0) \
            * np.clip((0.95 - L) / 0.15, 0.0, 1.0)
        skin = np.clip(hue_w * chroma_w * light_w, 0.0, 1.0)

        # Vibrance: stronger boost for muted colors, fades out near gamut
        sat = 1.0 + vibrance * 0.55 * np.clip(1.0 - chroma / 0.22, 0.0, 1.0)
        sat_eff = sat - (sat - 1.0) * skin * skin_protection * 0.85

        new_chroma = chroma * sat_eff

        # Soft cap on skin chroma — prevents the orange-face look
        cap = 0.145
        over = np.maximum(new_chroma - cap, 0.0)
        new_chroma = new_chroma - over * 0.6 * skin * skin_protection

        scale = new_chroma / np.maximum(chroma, 1e-9)
        a = a * scale
        b = b * scale

        # Split tone: cool shadows / warm highlights
        if shadow_tint > 0.0 or highlight_warmth > 0.0:
            sh_w = _smoothstep01((0.45 - L) / 0.45)
            hl_w = _smoothstep01((L - 0.65) / 0.35)
            a = a + hl_w * highlight_warmth * 0.012 \
                - sh_w * shadow_tint * 0.005
            b = b + hl_w * highlight_warmth * 0.035 \
                - sh_w * shadow_tint * 0.035

    lab = np.stack([L, a, b], axis=-1)
    return np.maximum(_oklab_to_linear_rgb(lab), 0.0)


# ============================================================================
# STAGE 5: Detail — texture (fine) + clarity (mid), single coherent stage
# ============================================================================

def apply_detail(srgb: np.ndarray, texture: float,
                 clarity: float) -> np.ndarray:
    """Two-scale luminance detail enhancement with halo suppression.

    texture: fine scale (~1px at 1K) — pores, fabric, hair
    clarity: mid scale (~2% of frame) — local punch / micro-contrast

    Detail amplitudes pass through tanh soft-limiting, which is what keeps
    edges crisp without the bright halos a plain unsharp mask produces.
    Luminance-only: chroma is untouched, so no color fringing.
    """
    if texture <= 0.0 and clarity <= 0.0:
        return srgb

    h, w = srgb.shape[:2]
    y = _luma(srgb)

    fine_r = max(1, round(min(h, w) / 900))
    mid_r = max(3, round(min(h, w) * 0.02))

    fine_base = _box_blur(y, fine_r)
    fine = y - fine_base
    mid = fine_base - _smooth(y, mid_r)

    limit = np.float32(0.18)
    new_y = y \
        + texture * 1.3 * limit * np.tanh(fine / limit) \
        + clarity * 0.9 * limit * np.tanh(mid / limit)

    scale = np.clip(new_y / np.maximum(y, 1e-4), 0.4, 2.5)[:, :, np.newaxis]
    return np.clip(srgb * scale, 0.0, 1.0).astype(np.float32)


# ============================================================================
# STAGE 6: Optics & Sensor
# ============================================================================

def apply_vignette(linear: np.ndarray, amount: float) -> np.ndarray:
    """Natural illumination falloff 1/(1+k·r²)², applied in linear light
    (where lens falloff physically happens)."""
    if amount <= 0.0:
        return linear

    h, w = linear.shape[:2]
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, np.newaxis]
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)[np.newaxis, :]
    r2 = (xx * xx + yy * yy) / 2.0  # corner = 1.0

    k = np.float32(0.35 * amount)
    falloff = 1.0 / (1.0 + k * r2) ** 2
    return (linear * falloff[:, :, np.newaxis]).astype(np.float32)


def apply_grain(srgb: np.ndarray, amount: float, seed: int) -> np.ndarray:
    """Photon-weighted luminance grain with a touch of chroma noise.

    Noise variance scales inversely with brightness (shadows are noisier,
    like a real sensor at base ISO). Mostly luminance noise — chroma noise
    is 30% of it, matching how camera denoisers leave residual noise.
    """
    if amount <= 0.0:
        return srgb

    rng = np.random.default_rng(seed)
    y = _luma(srgb)
    sigma = (amount * 0.010 * (0.35 + 0.65 * (1.0 - y))).astype(np.float32)

    noise_l = rng.standard_normal(y.shape, dtype=np.float32) * sigma
    noise_c = rng.standard_normal(srgb.shape, dtype=np.float32) \
        * (sigma[:, :, np.newaxis] * 0.3)

    return np.clip(srgb + noise_l[:, :, np.newaxis] + noise_c,
                   0.0, 1.0).astype(np.float32)


# ============================================================================
# MASTER PIPELINE
# ============================================================================

def process_iphone_realism(image: np.ndarray,
                           photographic_style: str = "Standard",
                           master_strength: float = 0.85,
                           seed: int = 0,
                           # White balance
                           enable_white_balance: bool = True,
                           wb_temperature: float = 0.12,
                           wb_tint: float = 0.0,
                           # Global tone
                           enable_tone: bool = True,
                           exposure: float = 0.05,
                           contrast: float = 0.15,
                           shadows: float = 0.35,
                           highlights: float = 0.5,
                           # Smart HDR (local)
                           enable_smart_hdr: bool = True,
                           hdr_strength: float = 0.35,
                           # Color science
                           enable_color: bool = True,
                           vibrance: float = 0.4,
                           skin_protection: float = 0.7,
                           shadow_tint: float = 0.25,
                           highlight_warmth: float = 0.2,
                           # Detail
                           enable_detail: bool = True,
                           texture: float = 0.35,
                           clarity: float = 0.2,
                           # Optics & sensor
                           enable_optics: bool = True,
                           grain: float = 0.2,
                           vignette: float = 0.25) -> np.ndarray:
    """Run the full iPhone 17 ISP pipeline on one (H, W, 3) float32 image.

    Order mirrors a real ISP: WB and tone in linear light, local HDR,
    color rendering, then display-referred detail/grain after encoding.
    master_strength is a single final blend between input and result.
    """
    p = resolve_style(photographic_style, {
        "wb_temperature": wb_temperature, "wb_tint": wb_tint,
        "exposure": exposure, "contrast": contrast,
        "shadows": shadows, "highlights": highlights,
        "hdr_strength": hdr_strength,
        "vibrance": vibrance, "skin_protection": skin_protection,
        "shadow_tint": shadow_tint, "highlight_warmth": highlight_warmth,
        "texture": texture, "clarity": clarity,
        "grain": grain, "vignette": vignette,
    })

    srgb_in = np.clip(image, 0.0, 1.0).astype(np.float32)
    lin = _srgb_to_linear(srgb_in)

    if enable_white_balance:
        lin = apply_white_balance(lin, p["wb_temperature"], p["wb_tint"])

    if enable_tone:
        lin = apply_global_tone(lin, p["exposure"], p["contrast"],
                                p["shadows"], p["highlights"])

    if enable_smart_hdr:
        lin = apply_smart_hdr(lin, p["hdr_strength"])

    if enable_color:
        lin = apply_color_science(lin, p["vibrance"], p["skin_protection"],
                                  p["shadow_tint"], p["highlight_warmth"],
                                  mono=p["_mono"])

    if enable_optics:
        lin = apply_vignette(lin, p["vignette"])

    out = _linear_to_srgb(np.clip(lin, 0.0, None))

    if enable_detail:
        out = apply_detail(out, p["texture"], p["clarity"])

    if enable_optics:
        out = apply_grain(out, p["grain"], seed)

    # iPhone "never crushes black": tiny display-domain black lift
    if enable_tone and p["shadows"] > 0.0:
        black_lift = np.float32(0.02 * p["shadows"])
        out = black_lift + (1.0 - black_lift) * out

    ms = np.float32(np.clip(master_strength, 0.0, 1.0))
    out = srgb_in * (1.0 - ms) + out * ms
    return np.clip(out, 0.0, 1.0).astype(np.float32)
