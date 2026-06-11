"""
LUT Engine — .cube 3D LUT Parser & Applicator
Zero-dependency implementation using numpy.

Supports the Adobe/IRIDAS .cube format (1.0 spec):
- LUT_3D_SIZE
- DOMAIN_MIN / DOMAIN_MAX
- RGB data lines

Interpolation is tetrahedral (the industry standard used by Resolve and
camera ISPs) — more accurate than trilinear, especially along the neutral
axis, because each lattice cell is split into 6 tetrahedra and only the 4
relevant corners contribute to each pixel.

Usage:
    lut, domain_min, domain_max = parse_cube_file("path/to/lut.cube")
    result = apply_lut_with_strength(image, lut, domain_min, domain_max,
                                     strength=0.85)
"""

import numpy as np
import os
from typing import Tuple


def parse_cube_file(filepath: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Parse a .cube LUT file into a numpy array.

    Returns:
        lut: np.ndarray of shape (N, N, N, 3) — indexed [b, g, r]
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


def _tetrahedral_chunk(pix: np.ndarray, lut: np.ndarray, n: int) -> np.ndarray:
    """Tetrahedral interpolation for a flat (P, 3) block of LUT coordinates
    already scaled to [0, n-1] index space. lut is indexed [b, g, r]."""
    idx0 = np.floor(pix).astype(np.int32)
    idx0 = np.minimum(idx0, n - 2) if n > 1 else idx0
    idx0 = np.maximum(idx0, 0)
    frac = (pix - idx0).astype(np.float32)

    r0, g0, b0 = idx0[:, 0], idx0[:, 1], idx0[:, 2]
    r1, g1, b1 = r0 + 1, g0 + 1, b0 + 1
    if n == 1:
        return lut[b0 * 0, g0 * 0, r0 * 0]
    dr, dg, db = frac[:, 0], frac[:, 1], frac[:, 2]

    out = np.empty((pix.shape[0], 3), dtype=np.float32)

    # Each lattice cell splits into 6 tetrahedra by the ordering of the
    # fractional coordinates. Only 4 corners are fetched per pixel.
    # Corner naming: cXYZ means (r + X, g + Y, b + Z).
    cases = [
        # condition,                corners (as index tuples),                weights
        (lambda: (dr >= dg) & (dg >= db),
         [(b0, g0, r0), (b0, g0, r1), (b0, g1, r1), (b1, g1, r1)],
         lambda r, g, b: (1 - r, r - g, g - b, b)),
        (lambda: (dr >= db) & (db > dg),
         [(b0, g0, r0), (b0, g0, r1), (b1, g0, r1), (b1, g1, r1)],
         lambda r, g, b: (1 - r, r - b, b - g, g)),
        (lambda: (db > dr) & (dr >= dg),
         [(b0, g0, r0), (b1, g0, r0), (b1, g0, r1), (b1, g1, r1)],
         lambda r, g, b: (1 - b, b - r, r - g, g)),
        (lambda: (dg > dr) & (dr >= db),
         [(b0, g0, r0), (b0, g1, r0), (b0, g1, r1), (b1, g1, r1)],
         lambda r, g, b: (1 - g, g - r, r - b, b)),
        (lambda: (dg >= db) & (db > dr),
         [(b0, g0, r0), (b0, g1, r0), (b1, g1, r0), (b1, g1, r1)],
         lambda r, g, b: (1 - g, g - b, b - r, r)),
        (lambda: (db > dg) & (dg > dr),
         [(b0, g0, r0), (b1, g0, r0), (b1, g1, r0), (b1, g1, r1)],
         lambda r, g, b: (1 - b, b - g, g - r, r)),
    ]

    assigned = np.zeros(pix.shape[0], dtype=bool)
    for cond, corners, weight_fn in cases:
        m = cond() & ~assigned
        if not np.any(m):
            continue
        assigned |= m
        rm, gm, bm = dr[m], dg[m], db[m]
        w0, w1, w2, w3 = weight_fn(rm, gm, bm)
        c0 = lut[corners[0][0][m], corners[0][1][m], corners[0][2][m]]
        c1 = lut[corners[1][0][m], corners[1][1][m], corners[1][2][m]]
        c2 = lut[corners[2][0][m], corners[2][1][m], corners[2][2][m]]
        c3 = lut[corners[3][0][m], corners[3][1][m], corners[3][2][m]]
        out[m] = (c0 * w0[:, None] + c1 * w1[:, None]
                  + c2 * w2[:, None] + c3 * w3[:, None])

    return out


def apply_lut_3d(image: np.ndarray, lut: np.ndarray,
                 domain_min: np.ndarray, domain_max: np.ndarray) -> np.ndarray:
    """Apply a 3D LUT to an image using tetrahedral interpolation.

    Processes in chunks to keep peak memory flat regardless of image size.

    Args:
        image: float32 array (H, W, 3) in [0, 1]
        lut: float32 array (N, N, N, 3)
        domain_min: float32 array (3,)
        domain_max: float32 array (3,)

    Returns:
        float32 array (H, W, 3) in [0, 1]
    """
    h, w, _ = image.shape
    n = lut.shape[0]

    domain_range = domain_max - domain_min
    domain_range = np.where(domain_range < 1e-10, 1.0, domain_range)

    coords = (image.reshape(-1, 3) - domain_min) / domain_range * (n - 1)
    coords = np.clip(coords, 0, n - 1).astype(np.float32)

    out = np.empty_like(coords)
    chunk = 1 << 21  # ~2M pixels per block
    for start in range(0, coords.shape[0], chunk):
        out[start:start + chunk] = _tetrahedral_chunk(
            coords[start:start + chunk], lut, n)

    return np.clip(out.reshape(h, w, 3), 0.0, 1.0).astype(np.float32)


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
