# 📷 Camera Forensic Realism Engine v2

Makes AI-generated images look like they were shot on an **iPhone 15 Pro** by emulating Apple's ISP color science pipeline.

> No more "AI look" — this node applies the same sensor artifacts, tone curves, and color science that real camera hardware produces.

---

## ✨ Processing Stages

| # | Stage | What It Does |
|---|-------|-------------|
| 1 | **White Balance** | iPhone warm daylight bias (temperature + tint) |
| 2 | **Tone Mapping** | S-curve with filmic highlight rolloff + shadow lifting |
| 3 | **Display P3 Color** | Wider gamut rendering via CIE XYZ transforms (richer reds/greens) |
| 4 | **Smart HDR** | Local tone mapping for micro-contrast and detail pop |
| 5 | **Real Tone** | Skin-targeted rendering with HSL detection (warm, not orange) |
| 6 | **ISP Sharpening** | Luminance-only unsharp mask (Apple crispness) |
| 7 | **Sensor FX** | Subtle luminance noise + gentle f/1.78 vignette |

---

## 🚀 Installation

### Option 1: Git Clone (Recommended)

Open a terminal and navigate to your ComfyUI custom nodes folder:

```bash
cd ComfyUI/custom_nodes
```

Clone this repository:

```bash
git clone https://github.com/MONKEYFOREVER2/ComfyUI-CameraForensicRealism.git
```

Install dependencies:

```bash
cd ComfyUI-CameraForensicRealism
pip install -r requirements.txt
```

Restart ComfyUI.

### Option 2: Manual Download

1. Click the green **Code** button at the top of this page
2. Select **Download ZIP**
3. Extract the ZIP into your `ComfyUI/custom_nodes/` folder
4. Make sure the folder is named `ComfyUI-CameraForensicRealism`
5. Install dependencies:
   ```bash
   cd ComfyUI/custom_nodes/ComfyUI-CameraForensicRealism
   pip install -r requirements.txt
   ```
6. Restart ComfyUI

### Option 3: ComfyUI Manager

If you have [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) installed:

1. Open ComfyUI Manager
2. Click **Install Custom Nodes**
3. Search for `Camera Forensic Realism`
4. Click **Install**
5. Restart ComfyUI

---

## 🎯 Finding the Node

Once installed, find the node in the ComfyUI menu:

**Right-click** → **Add Node** → **image/forensic** → **Camera Forensic Realism Engine**

---

## ⚡ Quick Start

1. Build your workflow as normal (generate/upscale/detail your image)
2. Place the **Camera Forensic Realism Engine** node **after** your detailers/post-processing and **before** SaveImage
3. Connect your image output to the node's input
4. That's it — defaults are tuned for **iPhone 15 Pro Standard** style

### Recommended Workflow Position

```
[Generate] → [Upscale] → [FaceDetailer] → [📷 Camera Forensic Realism] → [SaveImage]
```

---

## 🔧 Parameters

### Master Controls
| Parameter | Default | Description |
|-----------|---------|-------------|
| `master_strength` | `0.7` | Scales all effects globally. **0.6–0.8 recommended** |
| `seed` | `0` | Random seed for noise reproducibility |

### Tone Mapping
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_tone_mapping` | `True` | iPhone S-curve: lifts shadows, compresses highlights |
| `tone_strength` | `0.6` | Tone curve intensity (0.5–0.7 = natural iPhone) |
| `highlight_rolloff` | `0.5` | Smooth highlight compression — prevents blown whites |
| `shadow_lift` | `0.4` | Raises black level — iPhone never crushes pure black |
| `contrast` | `0.5` | Mid-tone contrast punch |

### Display P3 Color
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_p3_color` | `True` | Wider gamut rendering via CIE XYZ transform |
| `color_strength` | `0.5` | P3 color rendering intensity |
| `color_saturation` | `0.3` | Gamut saturation boost — keep low for realism |
| `color_warmth` | `0.3` | Apple warm color bias |

### Smart HDR
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_local_tone` | `True` | Local contrast like Apple's multi-frame HDR |
| `local_tone_strength` | `0.35` | Local contrast / HDR intensity |
| `detail_boost` | `0.4` | Micro-detail enhancement — texture pop |

### Real Tone (Skin)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_skin_rendering` | `True` | Natural warm skin — prevents orange cast |
| `skin_strength` | `0.5` | Skin rendering intensity |
| `skin_warmth` | `0.4` | Skin warmth / natural glow |

### Deep Fusion
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_deep_fusion` | `True` | High-freq texture crunch (fabric, pores) |
| `fusion_strength` | `0.6` | Texture amplification strength |
| `fusion_texture_freq` | `0.5` | Which texture thicknesses get enhanced |

### White Balance
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_white_balance` | `True` | iPhone AWB — warm daylight bias |
| `wb_strength` | `0.5` | White balance correction strength |
| `wb_temperature` | `0.25` | Cool (blue) ← → Warm (orange). iPhone ≈ 0.2–0.3 |
| `wb_tint` | `0.0` | Green ← → Magenta. 0 = neutral |

### Color Grading
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_color_grading` | `True` | Blue-tinted blacks + warm golden highlights |
| `blue_shadows` | `0.4` | Blue tint in darks — the iPhone blue-black look |
| `warm_highlights` | `0.3` | Golden warmth in brights |

### ISP Sharpening
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_sharpening` | `True` | Apple-style luminance sharpening |
| `sharpen_strength` | `0.3` | Sharpening intensity |

### Sensor FX
| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_sensor` | `True` | Subtle luminance noise + lens vignette |
| `sensor_strength` | `0.25` | Overall sensor effect intensity |
| `sensor_noise` | `0.3` | Luminance noise — very subtle on iPhone |
| `sensor_vignette` | `0.4` | Lens vignette — f/1.78 falloff |

---

## 🎨 LUT Color Grading (NEW)

This pack includes two dedicated LUT nodes for applying `.cube` 3D LUTs — plus a bundled **iPhone 15 Pro Standard** LUT baked from our color science pipeline.

### LUT Workflow

```
[🎨 LUT Loader] → [🎨 LUT Apply] → [SaveImage]
                        ↑
                    [Your Image]
```

### 🎨 LUT Loader

| Parameter | Description |
|-----------|-------------|
| `lut_name` | Dropdown of `.cube` files from the bundled `luts/` folder |

**Output:** `LUT_DATA` — connect to LUT Apply

### 🎨 LUT Apply

| Parameter | Default | Description |
|-----------|---------|-------------|
| `image` | — | Your image input |
| `lut_data` | — | Connect from LUT Loader |
| `strength` | `0.85` | LUT intensity (0.0 = original, 1.0 = full effect) |

**Output:** `IMAGE`

### Adding Custom LUTs

Drop any `.cube` 3D LUT file into the `luts/` folder inside this node pack and restart ComfyUI. It will appear in the LUT Loader dropdown automatically.

---

## 📋 Requirements

- **ComfyUI** (latest version recommended)
- **Python 3.10+**
- **numpy** and **torch** (already included with ComfyUI)
- Additional dependencies listed in `requirements.txt`

---

## 🤝 Contributing

Pull requests are welcome! If you'd like to add new camera profiles, custom LUTs, or improve the processing pipeline, feel free to open an issue or PR.

## 📄 License

MIT License — free to use, modify, and distribute.
