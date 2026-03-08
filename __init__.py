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
"""

from .nodes import CameraForensicRealismEngine

NODE_CLASS_MAPPINGS = {
    "CameraForensicRealismEngine": CameraForensicRealismEngine,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CameraForensicRealismEngine": "🔬 Camera Forensic Realism Engine",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
