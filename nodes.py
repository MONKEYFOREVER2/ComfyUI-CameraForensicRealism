"""
Camera Forensic Realism Engine - ComfyUI Node Definition v4
iPhone 17 ISP color science + Photographic Styles + custom themed UI.
"""

import numpy as np
import torch
import os

try:
    from .forensic_engine import process_iphone_realism, PHOTOGRAPHIC_STYLES
    from .lut_engine import parse_cube_file, apply_lut_with_strength
except ImportError:
    from forensic_engine import process_iphone_realism, PHOTOGRAPHIC_STYLES
    from lut_engine import parse_cube_file, apply_lut_with_strength


class CameraForensicRealismEngine:
    """
    Camera Forensic Realism Engine
    Makes AI images look like iPhone 17 photos — honest color science only.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),

                # ===================== MASTER =====================
                "photographic_style": (list(PHOTOGRAPHIC_STYLES.keys()), {
                    "default": "Standard",
                    "tooltip": "iPhone 17 Photographic Style. Undertones (Amber/Gold/Rose Gold/Cool Rose/Neutral) steer warmth; moods (Vibrant/Natural/Luminous/Dramatic/Quiet/Cozy/Ethereal/B&W) steer tone+color. Applied as offsets on top of your sliders."
                }),
                "master_strength": ("FLOAT", {
                    "default": 0.85, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Final blend between original and processed image. One honest mix control — per-stage sliders are absolute."
                }),
                "seed": ("INT", {
                    "default": 0, "min": 0, "max": 0xFFFFFFFF,
                    "tooltip": "Random seed for grain reproducibility"
                }),

                # ===================== WHITE BALANCE =====================
                "enable_white_balance": ("BOOLEAN", {
                    "default": True,
                    "label_on": "WHITE BAL: ON", "label_off": "WHITE BAL: OFF",
                    "tooltip": "Channel gains in linear light, luminance-preserving (warming doesn't brighten)"
                }),
                "wb_temperature": ("FLOAT", {
                    "default": 0.12, "min": -1.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Cool (blue) <----> Warm (orange). iPhone AWB sits slightly warm: ~0.1-0.15"
                }),
                "wb_tint": ("FLOAT", {
                    "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Green <----> Magenta. 0 = neutral"
                }),

                # ===================== GLOBAL TONE =====================
                "enable_tone": ("BOOLEAN", {
                    "default": True,
                    "label_on": "TONE: ON", "label_off": "TONE: OFF",
                    "tooltip": "Linear-light tone: exposure, shadow lift, midtone contrast, filmic highlight rolloff"
                }),
                "exposure": ("FLOAT", {
                    "default": 0.05, "min": -1.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Exposure in EV. iPhone meters slightly bright: ~0.05"
                }),
                "contrast": ("FLOAT", {
                    "default": 0.15, "min": -1.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Midtone contrast around the 0.18 photographic pivot. iPhone punch ~0.15"
                }),
                "shadows": ("FLOAT", {
                    "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Luminance-masked shadow lift + tiny black-point lift. iPhone never crushes blacks"
                }),
                "highlights": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Reinhard soft-knee highlight rolloff — smooth, monotonic, never blows out"
                }),

                # ===================== SMART HDR =====================
                "enable_smart_hdr": ("BOOLEAN", {
                    "default": True,
                    "label_on": "SMART HDR: ON", "label_off": "SMART HDR: OFF",
                    "tooltip": "Local tone mapping in log-luminance: compresses the base layer, keeps detail. Like Smart HDR 5 fusion"
                }),
                "hdr_strength": ("FLOAT", {
                    "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "How much local dynamic range compression (shadows up, highlights down — locally)"
                }),

                # ===================== COLOR SCIENCE =====================
                "enable_color": ("BOOLEAN", {
                    "default": True,
                    "label_on": "COLOR: ON", "label_off": "COLOR: OFF",
                    "tooltip": "Oklab color rendering: hue-preserving vibrance, skin protection, iPhone split-tone"
                }),
                "vibrance": ("FLOAT", {
                    "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Smart saturation: boosts muted colors more, leaves saturated ones alone. Hue-preserving (Oklab)"
                }),
                "skin_protection": ("FLOAT", {
                    "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Real skin mask (Oklab hue ~50°) that shields skin from vibrance and caps skin chroma — no orange faces"
                }),
                "shadow_tint": ("FLOAT", {
                    "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Cool/blue tint in shadows — the subtle iPhone blue-black signature"
                }),
                "highlight_warmth": ("FLOAT", {
                    "default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Golden warmth in highlights — complements the cool shadows"
                }),

                # ===================== DETAIL =====================
                "enable_detail": ("BOOLEAN", {
                    "default": True,
                    "label_on": "DETAIL: ON", "label_off": "DETAIL: OFF",
                    "tooltip": "Single coherent detail stage: fine texture + mid clarity, halo-suppressed, luminance-only"
                }),
                "texture": ("FLOAT", {
                    "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Fine-scale detail (~1px): pores, fabric, hair. The 'computational crunch'"
                }),
                "clarity": ("FLOAT", {
                    "default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Mid-scale local punch (~2% of frame). Keep low for natural look"
                }),

                # ===================== OPTICS & SENSOR =====================
                "enable_optics": ("BOOLEAN", {
                    "default": True,
                    "label_on": "OPTICS: ON", "label_off": "OPTICS: OFF",
                    "tooltip": "Lens vignette (linear light) + photon-weighted sensor grain"
                }),
                "grain": ("FLOAT", {
                    "default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Sensor noise, stronger in shadows like a real sensor. iPhone base ISO ~0.15-0.25"
                }),
                "vignette": ("FLOAT", {
                    "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Natural 1/(1+kr²)² illumination falloff applied in linear light. iPhone is well-corrected: keep low"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "apply_iphone_realism"
    CATEGORY = "image/forensic"

    DESCRIPTION = (
        "Camera Forensic Realism Engine v4\n\n"
        "iPhone 17 ISP emulation — honest color science:\n"
        "- White balance in linear light (luminance-preserving)\n"
        "- Filmic global tone (0.18 pivot, Reinhard rolloff)\n"
        "- Smart HDR local tone mapping (log-luminance base/detail)\n"
        "- Oklab color rendering (vibrance, skin protection, split-tone)\n"
        "- Two-scale halo-suppressed detail\n"
        "- Linear-light vignette + photon-weighted grain\n"
        "- 14 iPhone 17 Photographic Styles presets"
    )

    def apply_iphone_realism(self, image: torch.Tensor,
                             photographic_style: str,
                             master_strength: float,
                             seed: int,
                             enable_white_balance: bool,
                             wb_temperature: float,
                             wb_tint: float,
                             enable_tone: bool,
                             exposure: float,
                             contrast: float,
                             shadows: float,
                             highlights: float,
                             enable_smart_hdr: bool,
                             hdr_strength: float,
                             enable_color: bool,
                             vibrance: float,
                             skin_protection: float,
                             shadow_tint: float,
                             highlight_warmth: float,
                             enable_detail: bool,
                             texture: float,
                             clarity: float,
                             enable_optics: bool,
                             grain: float,
                             vignette: float):
        """Main processing function."""

        batch_size = image.shape[0]
        results = []

        for i in range(batch_size):
            img_np = image[i].cpu().numpy().astype(np.float32)

            processed = process_iphone_realism(
                image=img_np,
                photographic_style=photographic_style,
                master_strength=master_strength,
                seed=seed + i,
                enable_white_balance=enable_white_balance,
                wb_temperature=wb_temperature,
                wb_tint=wb_tint,
                enable_tone=enable_tone,
                exposure=exposure,
                contrast=contrast,
                shadows=shadows,
                highlights=highlights,
                enable_smart_hdr=enable_smart_hdr,
                hdr_strength=hdr_strength,
                enable_color=enable_color,
                vibrance=vibrance,
                skin_protection=skin_protection,
                shadow_tint=shadow_tint,
                highlight_warmth=highlight_warmth,
                enable_detail=enable_detail,
                texture=texture,
                clarity=clarity,
                enable_optics=enable_optics,
                grain=grain,
                vignette=vignette,
            )

            results.append(torch.from_numpy(processed))

        output = torch.stack(results, dim=0)
        return (output,)


# ============================================================================
# LUT Loader Node
# ============================================================================

class LUTLoader:
    """
    LUT Loader — Load .cube 3D LUT files.
    Scans the bundled luts/ folder and presents a dropdown selector.
    """

    LUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "luts")

    @classmethod
    def _get_lut_list(cls):
        """Discover all .cube files in the luts/ directory."""
        luts_dir = cls.LUTS_DIR
        if not os.path.isdir(luts_dir):
            return ["No LUTs found"]
        files = [f for f in os.listdir(luts_dir)
                 if f.lower().endswith('.cube') and os.path.isfile(os.path.join(luts_dir, f))]
        files.sort()
        return files if files else ["No LUTs found"]

    @classmethod
    def INPUT_TYPES(cls):
        lut_files = cls._get_lut_list()
        return {
            "required": {
                "lut_name": (lut_files, {
                    "tooltip": "Select a .cube LUT. Note: 'AppleLog2_to_Rec709' is a technical conversion LUT — it expects Apple Log footage as input, not regular sRGB images."
                }),
            },
        }

    RETURN_TYPES = ("LUT_DATA",)
    RETURN_NAMES = ("lut_data",)
    FUNCTION = "load_lut"
    CATEGORY = "image/forensic"

    DESCRIPTION = (
        "LUT Loader\n\n"
        "Loads a .cube 3D LUT file from the bundled luts/ folder.\n"
        "Connect the output to a LUT Apply node.\n\n"
        "Bundled LUTs:\n"
        "- AppleLog2_to_Rec709: official Apple Log -> Rec.709 conversion.\n"
        "  Only correct on Apple Log footage, NOT on regular sRGB images.\n"
        "- Portra 800: creative film-emulation look for sRGB images.\n\n"
        "Drop your own .cube files into luts/ and restart ComfyUI."
    )

    def load_lut(self, lut_name: str):
        """Load and parse the selected .cube LUT file."""
        filepath = os.path.join(self.LUTS_DIR, lut_name)

        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"LUT file not found: {filepath}")

        lut, domain_min, domain_max = parse_cube_file(filepath)

        lut_data = {
            "lut": lut,
            "domain_min": domain_min,
            "domain_max": domain_max,
            "name": lut_name,
            "path": filepath,
        }

        print(f"🎨 LUT Loader: Loaded '{lut_name}' ({lut.shape[0]}³ grid)")
        return (lut_data,)


# ============================================================================
# LUT Apply Node
# ============================================================================

class LUTApply:
    """
    LUT Apply — Apply a loaded 3D LUT to an image with adjustable strength.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "lut_data": ("LUT_DATA",),
                "strength": ("FLOAT", {
                    "default": 0.85, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "LUT intensity. 0.0 = original, 1.0 = full LUT effect."
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "apply_lut"
    CATEGORY = "image/forensic"

    DESCRIPTION = (
        "LUT Apply\n\n"
        "Applies a 3D LUT (from LUT Loader) to your image using\n"
        "tetrahedral interpolation — the industry-standard method\n"
        "(Resolve, camera ISPs), more accurate than trilinear.\n\n"
        "Strength controls the blend between original and LUT-graded."
    )

    def apply_lut(self, image: torch.Tensor, lut_data: dict, strength: float):
        """Apply the loaded LUT to each image in the batch."""
        lut = lut_data["lut"]
        domain_min = lut_data["domain_min"]
        domain_max = lut_data["domain_max"]
        lut_name = lut_data.get("name", "Unknown")

        batch_size = image.shape[0]
        results = []

        for i in range(batch_size):
            img_np = image[i].cpu().numpy().astype(np.float32)
            img_np = np.clip(img_np, 0.0, 1.0)

            processed = apply_lut_with_strength(img_np, lut, domain_min, domain_max, strength)
            results.append(torch.from_numpy(processed))

        output = torch.stack(results, dim=0)
        print(f"🎨 LUT Apply: Applied '{lut_name}' at {strength:.0%} strength")
        return (output,)
