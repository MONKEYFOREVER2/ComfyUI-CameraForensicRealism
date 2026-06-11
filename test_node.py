# -*- coding: utf-8 -*-
"""Camera Forensic Realism Engine v4 - Test Suite"""

import sys, os, io, time

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np


def make_test_image(h=256, w=256):
    img = np.zeros((h, w, 3), dtype=np.float32)
    img[:, :, 0] = np.linspace(0.3, 0.8, w)[np.newaxis, :]
    img[:, :, 1] = np.linspace(0.25, 0.65, w)[np.newaxis, :]
    img[:, :, 2] = np.linspace(0.2, 0.5, w)[np.newaxis, :]
    img[:h//4, :, :] = [0.7, 0.8, 0.95]      # Sky highlight
    img[3*h//4:, :, :] = [0.08, 0.06, 0.05]  # Dark shadow
    cy, cx = h // 2, w // 2
    img[cy-30:cy+30, cx-30:cx+30, :] = [0.76, 0.57, 0.45]  # Skin
    return np.clip(img, 0.0, 1.0)


def check(out, shape, name):
    ok = True
    if out.shape != shape: print(f"  [FAIL] {name}: shape {out.shape}"); ok = False
    if out.dtype != np.float32: print(f"  [FAIL] {name}: dtype {out.dtype}"); ok = False
    if np.any(np.isnan(out)) or np.any(np.isinf(out)): print(f"  [FAIL] {name}: NaN/Inf"); ok = False
    if out.min() < 0 or out.max() > 1: print(f"  [FAIL] {name}: range [{out.min():.4f},{out.max():.4f}]"); ok = False
    if ok: print(f"  [PASS] {name}")
    return ok


def test_box_blur():
    print("\n--- Test 1: Box Blur (centered, edge-safe) ---")
    from forensic_engine import _box_blur
    ok = True
    # Constant image must stay constant (old version darkened borders)
    const = np.full((64, 64), 0.5, dtype=np.float32)
    r = _box_blur(const, 5)
    if np.max(np.abs(r - 0.5)) > 1e-5:
        print(f"  [FAIL] Constant image changed (max err {np.max(np.abs(r-0.5)):.6f})"); ok = False
    else:
        print("  [PASS] Constant image unchanged (no border darkening)")
    # Impulse response must be centered (old version shifted diagonally)
    imp = np.zeros((65, 65), dtype=np.float32)
    imp[32, 32] = 1.0
    r = _box_blur(imp, 4)
    cy, cx = np.unravel_index(np.argmax(r), r.shape)
    if (cy, cx) != (32, 32):
        # box is flat — check center of mass instead
        ys, xs = np.nonzero(r)
        cy, cx = ys.mean(), xs.mean()
    if abs(cy - 32) > 0.51 or abs(cx - 32) > 0.51:
        print(f"  [FAIL] Blur not centered: peak at ({cy},{cx})"); ok = False
    else:
        print(f"  [PASS] Blur centered at ({cy:.1f},{cx:.1f})")
    return ok


def test_oklab_roundtrip():
    print("\n--- Test 2: Oklab Round-Trip ---")
    from forensic_engine import _linear_rgb_to_oklab, _oklab_to_linear_rgb
    rng = np.random.default_rng(7)
    rgb = rng.random((32, 32, 3)).astype(np.float32)
    back = _oklab_to_linear_rgb(_linear_rgb_to_oklab(rgb))
    err = np.max(np.abs(back - rgb))
    if err < 1e-4:
        print(f"  [PASS] Round-trip max error {err:.2e}")
        return True
    print(f"  [FAIL] Round-trip max error {err:.2e}")
    return False


def test_white_balance():
    print("\n--- Test 3: White Balance ---")
    from forensic_engine import apply_white_balance, _luma
    img = np.full((32, 32, 3), 0.25, dtype=np.float32)
    r = apply_white_balance(img, 0.5, 0.0)
    ok = True
    if not (r[0, 0, 0] > img[0, 0, 0] and r[0, 0, 2] < img[0, 0, 2]):
        print("  [FAIL] Warm temp should raise R, lower B"); ok = False
    else:
        print(f"  [PASS] Warm WB (R: {img[0,0,0]:.3f}->{r[0,0,0]:.3f}, B: {img[0,0,2]:.3f}->{r[0,0,2]:.3f})")
    lum_err = abs(float(_luma(r).mean()) - float(_luma(img).mean()))
    if lum_err > 0.005:
        print(f"  [FAIL] Luminance not preserved (err {lum_err:.4f})"); ok = False
    else:
        print(f"  [PASS] Luminance preserved (err {lum_err:.5f})")
    return ok


def test_global_tone():
    print("\n--- Test 4: Global Tone ---")
    from forensic_engine import apply_global_tone
    ramp = np.linspace(0, 1.4, 128, dtype=np.float32)
    img = np.stack([ramp]*3, axis=-1)[np.newaxis, :, :]
    r = apply_global_tone(img, exposure=0.0, contrast=0.2, shadows=0.4, highlights=0.6)
    ok = True
    # Shadows lifted
    if r[0, 2, 0] <= img[0, 2, 0]:
        print("  [FAIL] Shadows not lifted"); ok = False
    else:
        print(f"  [PASS] Shadow lift ({img[0,2,0]:.4f} -> {r[0,2,0]:.4f})")
    # Highlights compressed below input, never above 1
    if r[0, -1, 0] >= img[0, -1, 0] or r.max() > 1.0 + 1e-5:
        print(f"  [FAIL] Highlight rolloff broken (in {img[0,-1,0]:.3f} out {r[0,-1,0]:.3f})"); ok = False
    else:
        print(f"  [PASS] Highlight rolloff ({img[0,-1,0]:.3f} -> {r[0,-1,0]:.4f}, max {r.max():.4f})")
    # Monotonic (the old soft-clip was non-monotonic above 1.0)
    if np.any(np.diff(r[0, :, 0]) < -1e-6):
        print("  [FAIL] Tone curve not monotonic"); ok = False
    else:
        print("  [PASS] Tone curve monotonic")
    return ok


def test_smart_hdr():
    print("\n--- Test 5: Smart HDR ---")
    from forensic_engine import apply_smart_hdr, _srgb_to_linear, _luma
    img = _srgb_to_linear(make_test_image())
    r = apply_smart_hdr(img, 0.6)
    ok = True
    if np.any(np.isnan(r)) or np.any(np.isinf(r)):
        print("  [FAIL] NaN/Inf"); ok = False
    dark_before = float(_luma(img[200:, :, :]).mean())
    dark_after = float(_luma(r[200:, :, :]).mean())
    if dark_after > dark_before:
        print(f"  [PASS] Dark region lifted ({dark_before:.4f} -> {dark_after:.4f})")
    else:
        print(f"  [FAIL] Dark region not lifted ({dark_before:.4f} -> {dark_after:.4f})"); ok = False
    return ok


def test_color_science():
    print("\n--- Test 6: Color Science (Oklab) ---")
    from forensic_engine import (apply_color_science, _srgb_to_linear,
                                 _linear_rgb_to_oklab)
    ok = True
    # Vibrance boosts chroma of a muted color
    muted = _srgb_to_linear(np.full((16, 16, 3), [0.55, 0.5, 0.45], dtype=np.float32))
    r = apply_color_science(muted, vibrance=0.8, skin_protection=0.0,
                            shadow_tint=0.0, highlight_warmth=0.0)
    c0 = np.hypot(*_linear_rgb_to_oklab(muted)[0, 0, 1:])
    c1 = np.hypot(*_linear_rgb_to_oklab(r)[0, 0, 1:])
    if c1 > c0:
        print(f"  [PASS] Vibrance boosts muted chroma ({c0:.4f} -> {c1:.4f})")
    else:
        print(f"  [FAIL] Vibrance had no effect ({c0:.4f} -> {c1:.4f})"); ok = False
    # Skin protection attenuates the boost on skin colors
    skin = _srgb_to_linear(np.full((16, 16, 3), [0.76, 0.57, 0.45], dtype=np.float32))
    r_unprot = apply_color_science(skin, 0.8, 0.0, 0.0, 0.0)
    r_prot = apply_color_science(skin, 0.8, 1.0, 0.0, 0.0)
    d_unprot = float(np.abs(r_unprot - skin).mean())
    d_prot = float(np.abs(r_prot - skin).mean())
    if d_prot < d_unprot:
        print(f"  [PASS] Skin protection works (unprotected diff {d_unprot:.5f} > protected {d_prot:.5f})")
    else:
        print(f"  [FAIL] Skin protection ineffective ({d_unprot:.5f} vs {d_prot:.5f})"); ok = False
    # Split tone: shadows go blue (B up relative to R)
    dark = _srgb_to_linear(np.full((16, 16, 3), 0.08, dtype=np.float32))
    r = apply_color_science(dark, 0.0, 0.0, shadow_tint=1.0, highlight_warmth=0.0)
    if r[0, 0, 2] > r[0, 0, 0]:
        print(f"  [PASS] Shadow tint cools shadows (R {r[0,0,0]:.4f} < B {r[0,0,2]:.4f})")
    else:
        print(f"  [FAIL] Shadow tint missing (R {r[0,0,0]:.4f}, B {r[0,0,2]:.4f})"); ok = False
    # Mono kills chroma
    r = apply_color_science(skin, 0.5, 0.5, 0.0, 0.0, mono=True)
    spread = float(np.max(r[0, 0]) - np.min(r[0, 0]))
    if spread < 0.01:
        print(f"  [PASS] B&W rendering (channel spread {spread:.5f})")
    else:
        print(f"  [FAIL] B&W rendering leaks color (spread {spread:.5f})"); ok = False
    return ok


def test_detail():
    print("\n--- Test 7: Detail ---")
    from forensic_engine import apply_detail
    img = make_test_image()
    r = apply_detail(img, texture=0.8, clarity=0.4)
    ok = check(r, img.shape, "Detail")
    # Edge contrast across the shadow boundary should increase
    edge_in = float(np.abs(np.diff(img[:, 128, 0])).max())
    edge_out = float(np.abs(np.diff(r[:, 128, 0])).max())
    if edge_out >= edge_in:
        print(f"  [PASS] Edge contrast increased ({edge_in:.4f} -> {edge_out:.4f})")
    else:
        print(f"  [FAIL] No sharpening ({edge_in:.4f} -> {edge_out:.4f})"); ok = False
    return ok


def test_optics():
    print("\n--- Test 8: Optics & Sensor ---")
    from forensic_engine import apply_vignette, apply_grain, _srgb_to_linear
    ok = True
    img = np.full((128, 128, 3), 0.5, dtype=np.float32)
    v = apply_vignette(_srgb_to_linear(img), 0.6)
    center = float(v[64, 64, 0]); corner = float(v[0, 0, 0])
    if corner < center:
        print(f"  [PASS] Vignette darkens corners ({center:.4f} center vs {corner:.4f} corner)")
    else:
        print(f"  [FAIL] Vignette broken"); ok = False
    g1 = apply_grain(img, 0.5, seed=42)
    g2 = apply_grain(img, 0.5, seed=42)
    g3 = apply_grain(img, 0.5, seed=43)
    if np.array_equal(g1, g2) and not np.array_equal(g1, g3):
        print("  [PASS] Grain reproducible by seed")
    else:
        print("  [FAIL] Grain seeding broken"); ok = False
    if np.abs(g1 - img).mean() > 1e-5:
        print(f"  [PASS] Grain applied (mean dev {np.abs(g1-img).mean():.5f})")
    else:
        print("  [FAIL] Grain had no effect"); ok = False
    return ok


def test_styles():
    print("\n--- Test 9: Photographic Styles ---")
    from forensic_engine import PHOTOGRAPHIC_STYLES, resolve_style, process_iphone_realism
    ok = True
    expected = ["Standard", "Natural", "Vibrant", "Dramatic", "Amber", "Gold",
                "Rose Gold", "Cool Rose", "Neutral", "Muted B&W", "Stark B&W"]
    for name in expected:
        if name not in PHOTOGRAPHIC_STYLES:
            print(f"  [FAIL] Missing style '{name}'"); ok = False
    if ok:
        print(f"  [PASS] {len(PHOTOGRAPHIC_STYLES)} styles present")
    p = resolve_style("Amber", {"wb_temperature": 0.12, "wb_tint": 0.0,
                                "exposure": 0.0, "contrast": 0.0, "shadows": 0.3,
                                "highlights": 0.5, "hdr_strength": 0.3,
                                "vibrance": 0.4, "skin_protection": 0.7,
                                "shadow_tint": 0.2, "highlight_warmth": 0.2,
                                "texture": 0.3, "clarity": 0.2,
                                "grain": 0.2, "vignette": 0.2})
    if p["wb_temperature"] > 0.12:
        print(f"  [PASS] Amber warms temperature (0.12 -> {p['wb_temperature']:.2f})")
    else:
        print("  [FAIL] Amber offset not applied"); ok = False
    img = make_test_image(96, 96)
    std = process_iphone_realism(img, photographic_style="Standard", seed=1)
    bw = process_iphone_realism(img, photographic_style="Stark B&W", seed=1)
    chroma = float(np.abs(bw[:, :, 0] - bw[:, :, 1]).mean())
    if not np.array_equal(std, bw) and chroma < 0.02:
        print(f"  [PASS] Styles change output; B&W is neutral (chroma {chroma:.4f})")
    else:
        print(f"  [FAIL] Style differentiation broken (chroma {chroma:.4f})"); ok = False
    return ok


def test_pipeline():
    print("\n--- Test 10: Full Pipeline ---")
    from forensic_engine import process_iphone_realism
    img = make_test_image()
    t0 = time.time()
    r = process_iphone_realism(img, master_strength=0.85, seed=42)
    elapsed = time.time() - t0
    ok = check(r, img.shape, f"Pipeline ({elapsed:.2f}s)")
    print(f"  Total diff: {np.mean(np.abs(r-img)):.4f}")
    # master_strength=0 must return the input untouched
    r0 = process_iphone_realism(img, master_strength=0.0, seed=42)
    if np.max(np.abs(r0 - img)) < 1e-5:
        print("  [PASS] master_strength=0 is a true bypass")
    else:
        print(f"  [FAIL] master_strength=0 changed image ({np.max(np.abs(r0-img)):.5f})"); ok = False
    return ok


def test_node():
    print("\n--- Test 11: ComfyUI Node ---")
    try: import torch
    except ImportError: print("  [SKIP] No PyTorch"); return True
    from nodes import CameraForensicRealismEngine
    node = CameraForensicRealismEngine()
    inputs = node.INPUT_TYPES()["required"]
    print(f"  {len(inputs)} widgets")
    for name in ["photographic_style", "vibrance", "skin_protection", "texture"]:
        if name in inputs:
            print(f"  [PASS] '{name}' present")
        else:
            print(f"  [FAIL] '{name}' MISSING"); return False
    # Removed placebo/redundant params must be gone
    for name in ["enable_p3_color", "color_saturation", "wb_strength",
                 "tone_strength", "sensor_strength", "fusion_strength"]:
        if name in inputs:
            print(f"  [FAIL] Removed param '{name}' still present"); return False
    print("  [PASS] Placebo/redundant params removed")
    test_img = torch.rand(2, 128, 128, 3)
    result = node.apply_iphone_realism(
        image=test_img, photographic_style="Standard", master_strength=0.85, seed=42,
        enable_white_balance=True, wb_temperature=0.12, wb_tint=0.0,
        enable_tone=True, exposure=0.05, contrast=0.15, shadows=0.35, highlights=0.5,
        enable_smart_hdr=True, hdr_strength=0.35,
        enable_color=True, vibrance=0.4, skin_protection=0.7,
        shadow_tint=0.25, highlight_warmth=0.2,
        enable_detail=True, texture=0.35, clarity=0.2,
        enable_optics=True, grain=0.2, vignette=0.25,
    )
    out = result[0]
    if out.shape == test_img.shape: print(f"  [PASS] Shape: {tuple(out.shape)}")
    else: print(f"  [FAIL] Shape"); return False
    if 0 <= out.min() and out.max() <= 1: print(f"  [PASS] Range: [{out.min():.4f}, {out.max():.4f}]")
    else: print(f"  [FAIL] Range"); return False
    return True


def test_js_exists():
    print("\n--- Test 12: Custom UI ---")
    js_path = os.path.join(os.path.dirname(__file__), "js", "camera_forensic_ui.js")
    if not os.path.exists(js_path):
        print("  [FAIL] JS UI file missing")
        return False
    with open(js_path, encoding="utf-8") as f:
        content = f.read()
    ok = True
    for name in ["photographic_style", "vibrance", "skin_protection"]:
        if name not in content:
            print(f"  [FAIL] JS UI missing '{name}'"); ok = False
    if "enable_p3_color" in content:
        print("  [FAIL] JS UI still references removed params"); ok = False
    if ok:
        print(f"  [PASS] JS UI in sync ({len(content)} chars)")
    return ok


def _identity_lut(n=5):
    ax = np.linspace(0, 1, n, dtype=np.float32)
    b, g, r = np.meshgrid(ax, ax, ax, indexing='ij')
    return np.stack([r, g, b], axis=-1)  # indexed [b, g, r] -> (r, g, b)


def test_lut_parse():
    print("\n--- Test 13: LUT Parse ---")
    from lut_engine import parse_cube_file
    lut_path = os.path.join(os.path.dirname(__file__), "luts", "AppleLog2_to_Rec709_33_Grid.cube")
    if not os.path.exists(lut_path):
        print(f"  [FAIL] LUT file missing: {lut_path}"); return False
    lut, dmin, dmax = parse_cube_file(lut_path)
    ok = True
    if lut.shape != (33, 33, 33, 3):
        print(f"  [FAIL] Shape: {lut.shape}"); ok = False
    if np.any(np.isnan(lut)):
        print(f"  [FAIL] NaN in LUT"); ok = False
    if ok: print(f"  [PASS] LUT parsed: {lut.shape}")
    return ok


def test_lut_tetrahedral():
    print("\n--- Test 14: Tetrahedral LUT Interpolation ---")
    from lut_engine import apply_lut_3d
    dmin = np.zeros(3, dtype=np.float32)
    dmax = np.ones(3, dtype=np.float32)
    lut = _identity_lut(5)
    rng = np.random.default_rng(11)
    img = rng.random((64, 64, 3)).astype(np.float32)
    r = apply_lut_3d(img, lut, dmin, dmax)
    err = float(np.max(np.abs(r - img)))
    # Tetrahedral interpolation on an identity lattice must be exact
    if err < 1e-5:
        print(f"  [PASS] Identity LUT exact (max err {err:.2e})")
        return True
    print(f"  [FAIL] Identity LUT error too large ({err:.2e})")
    return False


def test_lut_strength():
    print("\n--- Test 15: LUT Strength ---")
    from lut_engine import parse_cube_file, apply_lut_with_strength
    lut_path = os.path.join(os.path.dirname(__file__), "luts", "AppleLog2_to_Rec709_33_Grid.cube")
    lut, dmin, dmax = parse_cube_file(lut_path)
    img = make_test_image()
    ok = True
    r0 = apply_lut_with_strength(img, lut, dmin, dmax, 0.0)
    if np.max(np.abs(r0 - img)) > 1e-6:
        print("  [FAIL] Strength 0 changed image"); ok = False
    else:
        print("  [PASS] Strength 0.0 = original")
    r05 = apply_lut_with_strength(img, lut, dmin, dmax, 0.5)
    r10 = apply_lut_with_strength(img, lut, dmin, dmax, 1.0)
    diff05 = np.mean(np.abs(r05 - img))
    diff10 = np.mean(np.abs(r10 - img))
    if diff05 < diff10 and diff10 > 1e-6:
        print(f"  [PASS] Strength scaling ({diff05:.4f} @ 0.5 < {diff10:.4f} @ 1.0)")
    else:
        print("  [FAIL] Strength scaling broken"); ok = False
    return ok


def test_lut_nodes():
    print("\n--- Test 16: LUT Nodes ---")
    from nodes import LUTLoader, LUTApply
    ok = True
    loader_inputs = LUTLoader.INPUT_TYPES()["required"]
    if "lut_name" in loader_inputs:
        print("  [PASS] LUTLoader has 'lut_name' input")
    else:
        print("  [FAIL] LUTLoader missing 'lut_name'"); ok = False
    apply_inputs = LUTApply.INPUT_TYPES()["required"]
    for name in ["image", "lut_data", "strength"]:
        if name in apply_inputs:
            print(f"  [PASS] LUTApply has '{name}' input")
        else:
            print(f"  [FAIL] LUTApply missing '{name}'"); ok = False
    return ok


if __name__ == "__main__":
    print("=" * 60)
    print("Camera Forensic Realism Engine v4 - Test Suite")
    print("=" * 60)
    tests = [test_box_blur, test_oklab_roundtrip, test_white_balance,
             test_global_tone, test_smart_hdr, test_color_science,
             test_detail, test_optics, test_styles, test_pipeline,
             test_node, test_js_exists,
             test_lut_parse, test_lut_tetrahedral, test_lut_strength,
             test_lut_nodes]
    results = []
    for t in tests:
        try: results.append(t())
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            import traceback; traceback.print_exc()
            results.append(False)
    print("\n" + "=" * 60)
    p = sum(1 for r in results if r)
    print(f"Results: {p}/{len(results)} tests passed")
    print("ALL PASSED!" if p == len(results) else "Some failed")
    print("=" * 60)
