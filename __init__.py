"""
ComfyUI-CameraForensicRealism
Camera Forensic Realism Engine — Custom Node for ComfyUI

Emulates the iPhone 17 ISP color pipeline so AI-generated images pick up
real camera color science instead of the flat "AI look".

Pipeline (v4):
1. White balance — linear light, luminance-preserving
2. Global tone — exposure, shadow lift, midtone contrast, filmic rolloff
3. Smart HDR — local tone mapping in log-luminance
4. Color science — Oklab vibrance, skin protection, iPhone split-tone
5. Detail — two-scale halo-suppressed luminance sharpening
6. Optics & sensor — linear-light vignette + photon-weighted grain
+ 14 iPhone 17 Photographic Styles presets

Also includes:
- LUT Loader: Load .cube 3D LUT files
- LUT Apply: Tetrahedral-interpolation LUT application with strength
"""

from .nodes import CameraForensicRealismEngine, LUTLoader, LUTApply

NODE_CLASS_MAPPINGS = {
    "CameraForensicRealismEngine": CameraForensicRealismEngine,
    "LUTLoader": LUTLoader,
    "LUTApply": LUTApply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CameraForensicRealismEngine": "📷 Camera Forensic Realism (iPhone 17)",
    "LUTLoader": "🎨 LUT Loader",
    "LUTApply": "🎨 LUT Apply",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
