"""
LUT Engine — .cube 3D LUT Parser & Applicator
Zero-dependency implementation using numpy trilinear interpolation.

Supports the Adobe/IRIDAS .cube format (1.0 spec):
- LUT_3D_SIZE
- DOMAIN_MIN / DOMAIN_MAX
- RGB data lines

Usage:
    lut, domain_min, domain_max = parse_cube_file("path/to/lut.cube")
    result = apply_lut_with_strength(image, lut, domain_min, domain_max, strength=0.85)
"""

import numpy as np
import os
from typing import Tuple


def parse_cube_file(filepath: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Parse a .cube LUT file into a numpy array.

    Returns:
        lut: np.ndarray of shape (N, N, N, 3) — the 3D LUT data
        domain_min: np.ndarray of shape (3,) — input domain minimum
        domain_max: np.ndarray of shape (3,) — input domain maximum

    The .cube format stores data in R-major order:
    R increments fastest, then G, then B (outermost).
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"LUT file not found: {filepath}")

    lut_size = None
    domain_min = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    domain_max = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    data_lines = []

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse keywords
            if line.startswith('TITLE'):
                continue
            elif line.startswith('LUT_3D_SIZE'):
                lut_size = int(line.split()[-1])
            elif line.startswith('LUT_1D_SIZE'):
                raise ValueError("1D LUTs are not supported. Please use a 3D .cube LUT.")
            elif line.startswith('DOMAIN_MIN'):
                parts = line.split()[1:]
                domain_min = np.array([float(x) for x in parts], dtype=np.float32)
            elif line.startswith('DOMAIN_MAX'):
                parts = line.split()[1:]
                domain_max = np.array([float(x) for x in parts], dtype=np.float32)
            else:
                # Try to parse as data line (3 floats)
                try:
                    parts = line.split()
                    if len(parts) >= 3:
                        r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                        data_lines.append([r, g, b])
                except ValueError:
                    continue  # Skip unparseable lines

    if lut_size is None:
        raise ValueError("No LUT_3D_SIZE found in .cube file")

    expected_count = lut_size ** 3
    if len(data_lines) != expected_count:
        raise ValueError(
            f"Expected {expected_count} data lines for size {lut_size}, "
            f"got {len(data_lines)}"
        )

    # Reshape into (N, N, N, 3) — R fastest, then G, then B
    lut = np.array(data_lines, dtype=np.float32).reshape(lut_size, lut_size, lut_size, 3)

    return lut, domain_min, domain_max


def apply_lut_3d(image: np.ndarray, lut: np.ndarray,
                  domain_min: np.ndarray, domain_max: np.ndarray) -> np.ndarray:
    """Apply a 3D LUT to an image using trilinear interpolation.

    Args:
        image: float32 array (H, W, 3) in [0, 1]
        lut: float32 array (N, N, N, 3)
        domain_min: float32 array (3,)
        domain_max: float32 array (3,)

    Returns:
        float32 array (H, W, 3) in [0, 1]
    """
    h, w, _ = image.shape
    n = lut.shape[0]  # LUT size

    # Normalize input to LUT domain [0, N-1]
    domain_range = domain_max - domain_min
    domain_range = np.where(domain_range < 1e-10, 1.0, domain_range)

    # Scale image values to LUT index space
    coords = (image - domain_min) / domain_range * (n - 1)
    coords = np.clip(coords, 0, n - 1)

    # Integer indices for the 8 corners of the interpolation cube
    idx0 = np.floor(coords).astype(np.int32)
    idx1 = np.minimum(idx0 + 1, n - 1)

    # Fractional parts for interpolation weights
    frac = coords - idx0.astype(np.float32)

    # Flatten for indexing
    r0, g0, b0 = idx0[:, :, 0], idx0[:, :, 1], idx0[:, :, 2]
    r1, g1, b1 = idx1[:, :, 0], idx1[:, :, 1], idx1[:, :, 2]
    fr, fg, fb = frac[:, :, 0], frac[:, :, 1], frac[:, :, 2]

    # Trilinear interpolation using the 8 corners
    # c000 = lut[b0, g0, r0], c100 = lut[b0, g0, r1], etc.
    c000 = lut[b0, g0, r0]
    c100 = lut[b0, g0, r1]
    c010 = lut[b0, g1, r0]
    c110 = lut[b0, g1, r1]
    c001 = lut[b1, g0, r0]
    c101 = lut[b1, g0, r1]
    c011 = lut[b1, g1, r0]
    c111 = lut[b1, g1, r1]

    # Expand fractional dims for broadcasting
    fr = fr[:, :, np.newaxis]
    fg = fg[:, :, np.newaxis]
    fb = fb[:, :, np.newaxis]

    # Interpolate along R axis
    c00 = c000 * (1 - fr) + c100 * fr
    c01 = c001 * (1 - fr) + c101 * fr
    c10 = c010 * (1 - fr) + c110 * fr
    c11 = c011 * (1 - fr) + c111 * fr

    # Interpolate along G axis
    c0 = c00 * (1 - fg) + c10 * fg
    c1 = c01 * (1 - fg) + c11 * fg

    # Interpolate along B axis
    result = c0 * (1 - fb) + c1 * fb

    return np.clip(result, 0.0, 1.0).astype(np.float32)


def apply_lut_with_strength(image: np.ndarray, lut: np.ndarray,
                             domain_min: np.ndarray, domain_max: np.ndarray,
                             strength: float = 1.0) -> np.ndarray:
    """Apply a 3D LUT with adjustable strength (opacity).

    Args:
        image: float32 array (H, W, 3) in [0, 1]
        lut: float32 array (N, N, N, 3)
        domain_min: float32 array (3,)
        domain_max: float32 array (3,)
        strength: 0.0 = original image, 1.0 = full LUT

    Returns:
        float32 array (H, W, 3) in [0, 1]
    """
    if strength <= 0:
        return image.copy()

    lut_result = apply_lut_3d(image, lut, domain_min, domain_max)

    if strength >= 1.0:
        return lut_result

    # Linear blend
    blended = image * (1.0 - strength) + lut_result * strength
    return np.clip(blended, 0.0, 1.0).astype(np.float32)
