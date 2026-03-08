# Camera Forensic Realism Engine v2

Makes AI-generated images look like they were shot on an **iPhone 15 Pro** by emulating Apple's ISP color science pipeline.

## Processing Stages

| # | Stage | What It Does |
|---|-------|-------------|
| 1 | **White Balance** | iPhone warm daylight bias (temperature + tint) |
| 2 | **Tone Mapping** | S-curve with filmic highlight rolloff + shadow lifting |
| 3 | **Display P3 Color** | Wider gamut rendering via CIE XYZ transforms (richer reds/greens) |
| 4 | **Smart HDR** | Local tone mapping for micro-contrast and detail pop |
| 5 | **Real Tone** | Skin-targeted rendering with HSL detection (warm, not orange) |
| 6 | **ISP Sharpening** | Luminance-only unsharp mask (Apple crispness) |
| 7 | **Sensor FX** | Subtle luminance noise + gentle f/1.78 vignette |

## Installation

Copy into `ComfyUI/custom_nodes/ComfyUI-CameraForensicRealism/` and restart ComfyUI.

Node appears under: **image/forensic** -> **Camera Forensic Realism Engine**

## Quick Start

Place after detailers/post-processing, before SaveImage. Defaults are tuned for iPhone 15 Pro Standard style.

**No extra dependencies** - uses only numpy + torch (built into ComfyUI).
