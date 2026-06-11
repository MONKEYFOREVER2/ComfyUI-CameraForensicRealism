# 📷 Camera Forensic Realism Engine v4

Makes AI-generated images look like they were shot on an **iPhone 17** by emulating Apple's ISP color pipeline — with honest, physically-grounded color science.

> No placebo sliders. Every stage in v4 does real, verifiable work: white balance and tone mapping in linear light, local HDR in log-luminance, color rendering in Oklab, and tetrahedral LUT interpolation.

---

## ✨ Processing Stages

| # | Stage | What It Does |
|---|-------|-------------|
| 1 | **White Balance** | Channel gains in **linear light**, luminance-preserving (warming doesn't brighten) |
| 2 | **Global Tone** | Exposure, shadow lift, midtone contrast around the 0.18 pivot, Reinhard highlight rolloff |
| 3 | **Smart HDR** | Durand-style local tone mapping in log-luminance — shadows up, highlights down, detail untouched |
| 4 | **Color Science** | **Oklab** rendering: hue-preserving vibrance, real skin protection, iPhone split-tone (cool shadows / warm highlights) |
| 5 | **Detail** | Single two-scale stage (texture + clarity) with tanh halo suppression, luminance-only |
| 6 | **Optics & Sensor** | Natural 1/(1+kr²)² vignette in linear light + photon-weighted grain |

Plus **14 iPhone 17 Photographic Styles** presets (undertones + moods) applied as offsets on top of your sliders.

### What changed from v2/v3

- ❌ **Removed the fake "Display P3" stage** — it converted sRGB→XYZ→P3 and back (a mathematical no-op) and the only real effect was a plain saturation multiply. Replaced with genuine Oklab vibrance.
- ❌ **Removed redundant multiplier sliders** (`wb_strength`, `tone_strength`, `sensor_strength`) — `master_strength` is now the one honest mix control.
- ❌ **Merged three overlapping sharpeners** (detail boost / Deep Fusion / ISP sharpening) into one coherent detail stage.
- 🐛 **Fixed the box blur** used by HDR and sharpening — it was a trailing window that shifted every blur diagonally and darkened the top/left borders.
- 🐛 **Fixed the non-monotonic highlight clip** that could cause banding above white.
- ✅ Skin handling is now an actual protection mask (Oklab hue ≈ 50°, plausible chroma/lightness) instead of a brightness filter on every warm pixel.

---

## 🚀 Installation

### Option 1: Git Clone (Recommended)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/MONKEYFOREVER2/ComfyUI-CameraForensicRealism.git
cd ComfyUI-CameraForensicRealism
pip install -r requirements.txt
```

Restart ComfyUI.

### Option 2: Manual Download

1. Click the green **Code** button → **Download ZIP**
2. Extract into `ComfyUI/custom_nodes/` as `ComfyUI-CameraForensicRealism`
3. `pip install -r requirements.txt`
4. Restart ComfyUI

---

## 🎯 Finding the Node

**Right-click** → **Add Node** → **image/forensic** → **📷 Camera Forensic Realism (iPhone 17)**

## ⚡ Quick Start

1. Place the node **after** your detailers/post-processing and **before** SaveImage
2. Pick a **Photographic Style** (start with `Standard`)
3. Defaults are tuned for the iPhone 17 look — adjust to taste

```
[Generate] → [Upscale] → [FaceDetailer] → [📷 Camera Forensic Realism] → [SaveImage]
```

---

## 🔧 Parameters

### Master
| Parameter | Default | Description |
|-----------|---------|-------------|
| `photographic_style` | `Standard` | iPhone 17 Photographic Style preset (see below) |
| `master_strength` | `0.85` | Final blend between original and processed image |
| `seed` | `0` | Grain reproducibility |

### Photographic Styles

**Moods:** `Standard`, `Natural`, `Luminous`, `Vibrant`, `Dramatic`, `Quiet`, `Cozy`, `Ethereal`, `Muted B&W`, `Stark B&W`
**Undertones:** `Amber`, `Gold`, `Rose Gold`, `Cool Rose`, `Neutral`

Styles are applied as offsets on top of your slider values, mirroring how Apple's 2nd-gen Photographic Styles re-tune the same pipeline.

### White Balance
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_white_balance` | `True` | Linear-light channel gains, luminance-preserving |
| `wb_temperature` | `0.12` | Cool (blue) ← → Warm (orange). iPhone AWB ≈ 0.1–0.15 |
| `wb_tint` | `0.0` | Green ← → Magenta |

### Global Tone
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_tone` | `True` | Linear-light tone mapping |
| `exposure` | `0.05` | EV adjustment — iPhone meters slightly bright |
| `contrast` | `0.15` | Midtone contrast around the 0.18 photographic pivot |
| `shadows` | `0.35` | Luminance-masked shadow lift + tiny black-point lift |
| `highlights` | `0.5` | Reinhard soft-knee rolloff — smooth, monotonic, never clips |

### Smart HDR
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_smart_hdr` | `True` | Local tone mapping in log-luminance |
| `hdr_strength` | `0.35` | Local dynamic range compression amount |

### Color Science (Oklab)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_color` | `True` | Perceptual color rendering |
| `vibrance` | `0.4` | Smart saturation — boosts muted colors more, hue-preserving |
| `skin_protection` | `0.7` | Shields skin from vibrance + caps skin chroma (no orange faces) |
| `shadow_tint` | `0.25` | Subtle cool/blue shadows — the iPhone blue-black signature |
| `highlight_warmth` | `0.2` | Golden warmth in highlights |

### Detail
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_detail` | `True` | Two-scale luminance detail, halo-suppressed |
| `texture` | `0.35` | Fine scale (~1px): pores, fabric, hair |
| `clarity` | `0.2` | Mid scale (~2% of frame): local punch |

### Optics & Sensor
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_optics` | `True` | Vignette + grain |
| `grain` | `0.2` | Photon-weighted noise, stronger in shadows |
| `vignette` | `0.25` | Natural falloff in linear light — iPhone is well-corrected, keep low |

---

## 🎨 LUT Nodes

Two dedicated nodes for applying `.cube` 3D LUTs with **tetrahedral interpolation** (the industry-standard method used by Resolve and camera ISPs — more accurate than trilinear, especially on the neutral axis).

### Recommended settings

I recommend setting the strength to around 0.05 to 0.10

```
[🎨 LUT Loader] → [🎨 LUT Apply] → [SaveImage]
                        ↑
                    [Your Image]
```

### 🎨 LUT Loader
| Parameter | Description |
|-----------|-------------|
| `lut_name` | Dropdown of `.cube` files from the `luts/` folder |

### 🎨 LUT Apply
| Parameter | Default | Description |
|-----------|---------|-------------|
| `strength` | `0.85` | 0.0 = original, 1.0 = full LUT |

### Bundled LUTs

| File | Type | Correct input |
|------|------|--------------|
| `AppleLog2_to_Rec709_33_Grid.cube` | Technical conversion | **Apple Log footage only** — do *not* apply to regular sRGB images |
| `Presetpro - Portra 800.cube` | Creative film look | Regular sRGB images |

Drop your own `.cube` files into `luts/` and restart ComfyUI.

---

## 📋 Requirements

- **ComfyUI** (latest version recommended)
- **Python 3.10+**
- **numpy** and **torch** (already included with ComfyUI)

## 🤝 Contributing

Pull requests are welcome — new Photographic Style tunings, LUTs, or pipeline improvements.

## 📄 License

MIT License — free to use, modify, and distribute.
