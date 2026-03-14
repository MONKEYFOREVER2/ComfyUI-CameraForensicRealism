"""
ComfyUI-CameraForensicRealism
Camera Forensic Realism Engine — Custom Node for ComfyUI

Injects real camera sensor fingerprints into AI-generated images to make
them forensically indistinguishable from real photographs.

Stages:
1. Bayer CFA demosaicing artifacts
2. Sensor noise (shot + read + dark current + hot pixels)
3. Camera-specific JPEG compression artifacts
4. cos⁴ lens vignetting with asymmetry
5. ISP color bias

Also includes:
- LUT Loader: Load .cube 3D LUT files (bundled iPhone 15 Pro LUT)
- LUT Apply: Apply LUTs with adjustable strength
"""

from .nodes import CameraForensicRealismEngine, LUTLoader, LUTApply

NODE_CLASS_MAPPINGS = {
    "CameraForensicRealismEngine": CameraForensicRealismEngine,
    "LUTLoader": LUTLoader,
    "LUTApply": LUTApply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CameraForensicRealismEngine": "🔬 Camera Forensic Realism Engine",
    "LUTLoader": "🎨 LUT Loader",
    "LUTApply": "🎨 LUT Apply",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

