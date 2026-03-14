"""
Camera Forensic Realism Engine - ComfyUI Node Definition v3
iPhone ISP color science with blue shadow tint + custom themed UI.
"""

import numpy as np
import torch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from forensic_engine import process_iphone_realism


class CameraForensicRealismEngine:
    """
    Camera Forensic Realism Engine
    Makes AI images look like iPhone 15 Pro photos.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),

                # ===================== MASTER =====================
                "master_strength": ("FLOAT", {
                    "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "MASTER CONTROL - Scales all effects. 0.6-0.8 recommended."
                }),
                "seed": ("INT", {
                    "default": 0, "min": 0, "max": 0xFFFFFFFF,
                    "tooltip": "Random seed for noise reproducibility"
                }),

                # ===================== TONE MAPPING =====================
                "enable_tone_mapping": ("BOOLEAN", {
                    "default": True,
                    "label_on": "TONE CURVE: ON",
                    "label_off": "TONE CURVE: OFF",
                    "tooltip": "iPhone S-curve: lifts shadows, compresses highlights, punchy mids"
                }),
                "tone_strength": ("FLOAT", {
                    "default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "How much tone curve to apply. 0.5-0.7 = natural iPhone"
                }),
                "highlight_rolloff": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Smooth highlight compression - prevents blown-out whites"
                }),
                "shadow_lift": ("FLOAT", {
                    "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Raises black level - iPhone never crushes pure black"
                }),
                "contrast": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Mid-tone contrast punch"
                }),

                # ===================== P3 COLOR =====================
                "enable_p3_color": ("BOOLEAN", {
                    "default": True,
                    "label_on": "P3 COLOR: ON",
                    "label_off": "P3 COLOR: OFF",
                    "tooltip": "Display P3 gamut - richer reds/greens via CIE XYZ transform"
                }),
                "color_strength": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "P3 color rendering intensity"
                }),
                "color_saturation": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Wider gamut saturation boost - keep low for realism"
                }),
                "color_warmth": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Apple warm color bias - signature iPhone warmth"
                }),

                # ===================== SMART HDR =====================
                "enable_local_tone": ("BOOLEAN", {
                    "default": True,
                    "label_on": "SMART HDR: ON",
                    "label_off": "SMART HDR: OFF",
                    "tooltip": "Local contrast like Apple's multi-frame HDR fusion"
                }),
                "local_tone_strength": ("FLOAT", {
                    "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Local contrast/HDR intensity"
                }),
                "detail_boost": ("FLOAT", {
                    "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Micro-detail enhancement - texture pop"
                }),

                # ===================== SKIN =====================
                "enable_skin_rendering": ("BOOLEAN", {
                    "default": True,
                    "label_on": "REAL TONE: ON",
                    "label_off": "REAL TONE: OFF",
                    "tooltip": "Apple Real Tone - warm natural skin, prevents orange"
                }),
                "skin_strength": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Skin rendering intensity"
                }),
                "skin_warmth": ("FLOAT", {
                    "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Skin warmth - natural glow without oversaturation"
                }),

                # ===================== DEEP FUSION =====================
                "enable_deep_fusion": ("BOOLEAN", {
                    "default": True,
                    "label_on": "DEEP FUSION: ON",
                    "label_off": "DEEP FUSION: OFF",
                    "tooltip": "Isolate and crunch high-frequency textures (fabric, pores) without halos."
                }),
                "fusion_strength": ("FLOAT", {
                    "default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Texture amplification strength (the iPhone computational crunch)."
                }),
                "fusion_texture_freq": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Determines which texture thicknesses are crunched."
                }),

                # ===================== WHITE BALANCE =====================
                "enable_white_balance": ("BOOLEAN", {
                    "default": True,
                    "label_on": "WHITE BAL: ON",
                    "label_off": "WHITE BAL: OFF",
                    "tooltip": "iPhone AWB - warm daylight bias"
                }),
                "wb_strength": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "White balance correction strength"
                }),
                "wb_temperature": ("FLOAT", {
                    "default": 0.25, "min": -1.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Cool(blue) <----> Warm(orange). iPhone = ~0.2-0.3"
                }),
                "wb_tint": ("FLOAT", {
                    "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Green <----> Magenta tint. 0 = neutral"
                }),

                # ===================== COLOR GRADING =====================
                "enable_color_grading": ("BOOLEAN", {
                    "default": True,
                    "label_on": "COLOR GRADE: ON",
                    "label_off": "COLOR GRADE: OFF",
                    "tooltip": "iPhone signature: blue-tinted blacks + warm golden highlights"
                }),
                "blue_shadows": ("FLOAT", {
                    "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Blue tint in dark areas - the iPhone blue-black look"
                }),
                "warm_highlights": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Golden warmth in bright areas - complements blue shadows"
                }),

                # ===================== SHARPENING =====================
                "enable_sharpening": ("BOOLEAN", {
                    "default": True,
                    "label_on": "ISP SHARP: ON",
                    "label_off": "ISP SHARP: OFF",
                    "tooltip": "Apple-style luminance sharpening - crisp not crunchy"
                }),
                "sharpen_strength": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Sharpening intensity"
                }),

                # ===================== SENSOR =====================
                "enable_sensor": ("BOOLEAN", {
                    "default": True,
                    "label_on": "SENSOR FX: ON",
                    "label_off": "SENSOR FX: OFF",
                    "tooltip": "Subtle luminance noise + lens vignette"
                }),
                "sensor_strength": ("FLOAT", {
                    "default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Overall sensor effect intensity"
                }),
                "sensor_noise": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Luminance noise - very subtle on iPhone"
                }),
                "sensor_vignette": ("FLOAT", {
                    "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "Lens vignette - f/1.78 falloff"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "apply_iphone_realism"
    CATEGORY = "image/forensic"

    DESCRIPTION = (
        "Camera Forensic Realism Engine v3\n\n"
        "iPhone 15 Pro ISP emulation:\n"
        "- S-curve tone mapping (filmic highlight rolloff)\n"
        "- Display P3 color (CIE XYZ gamut transform)\n"
        "- Smart HDR local tone mapping\n"
        "- Real Tone skin rendering\n"
        "- Deep Fusion edge-preserving texture crunch\n"
        "- Blue shadow tint (iPhone blue-black look)\n"
        "- Warm golden highlights\n"
        "- ISP sharpening + subtle sensor FX"
    )

    def apply_iphone_realism(self, image: torch.Tensor,
                              master_strength: float,
                              seed: int,
                              enable_tone_mapping: bool,
                              tone_strength: float,
                              highlight_rolloff: float,
                              shadow_lift: float,
                              contrast: float,
                              enable_p3_color: bool,
                              color_strength: float,
                              color_saturation: float,
                              color_warmth: float,
                              enable_local_tone: bool,
                              local_tone_strength: float,
                              detail_boost: float,
                              enable_skin_rendering: bool,
                              skin_strength: float,
                              skin_warmth: float,
                              enable_deep_fusion: bool,
                              fusion_strength: float,
                              fusion_texture_freq: float,
                              enable_white_balance: bool,
                              wb_strength: float,
                              wb_temperature: float,
                              wb_tint: float,
                              enable_color_grading: bool,
                              blue_shadows: float,
                              warm_highlights: float,
                              enable_sharpening: bool,
                              sharpen_strength: float,
                              enable_sensor: bool,
                              sensor_strength: float,
                              sensor_noise: float,
                              sensor_vignette: float):
        """Main processing function."""

        batch_size = image.shape[0]
        results = []

        for i in range(batch_size):
            img_np = image[i].cpu().numpy().astype(np.float32)
            img_np = np.clip(img_np, 0.0, 1.0)

            processed = process_iphone_realism(
                image=img_np,
                master_strength=master_strength,
                enable_tone_mapping=enable_tone_mapping,
                tone_strength=tone_strength,
                highlight_rolloff=highlight_rolloff,
                shadow_lift=shadow_lift,
                contrast=contrast,
                enable_p3_color=enable_p3_color,
                color_strength=color_strength,
                color_saturation=color_saturation,
                color_warmth=color_warmth,
                enable_local_tone=enable_local_tone,
                local_tone_strength=local_tone_strength,
                detail_boost=detail_boost,
                enable_skin_rendering=enable_skin_rendering,
                skin_strength=skin_strength,
                skin_warmth=skin_warmth,
                enable_deep_fusion=enable_deep_fusion,
                fusion_strength=fusion_strength,
                fusion_texture_freq=fusion_texture_freq,
                enable_white_balance=enable_white_balance,
                wb_strength=wb_strength,
                wb_temperature=wb_temperature,
                wb_tint=wb_tint,
                enable_color_grading=enable_color_grading,
                blue_shadows=blue_shadows,
                warm_highlights=warm_highlights,
                enable_sharpening=enable_sharpening,
                sharpen_strength=sharpen_strength,
                enable_sensor=enable_sensor,
                sensor_strength=sensor_strength,
                sensor_noise=sensor_noise,
                sensor_vignette=sensor_vignette,
                seed=seed + i,
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

    def __init__(self):
        pass

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
                    "tooltip": "Select a .cube LUT file from the bundled luts/ folder"
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
        "Bundled LUT: iPhone 15 Pro Standard — baked from the\n"
        "Camera Forensic Realism Engine's color science pipeline."
    )

    def load_lut(self, lut_name: str):
        """Load and parse the selected .cube LUT file."""
        from lut_engine import parse_cube_file

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

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "lut_data": ("LUT_DATA",),
                "strength": ("FLOAT", {
                    "default": 0.85, "min": 0.0, "max": 1.0, "step": 0.01,
                    "display": "slider",
                    "tooltip": "LUT intensity. 0.0 = original, 1.0 = full LUT effect. 0.85 recommended."
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
        "trilinear interpolation for smooth, accurate color grading.\n\n"
        "Strength controls the blend between original and LUT-graded.\n"
        "0.85 = recommended for natural iPhone look."
    )

    def apply_lut(self, image: torch.Tensor, lut_data: dict, strength: float):
        """Apply the loaded LUT to each image in the batch."""
        from lut_engine import apply_lut_with_strength

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

