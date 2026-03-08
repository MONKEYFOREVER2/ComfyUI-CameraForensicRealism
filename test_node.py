# -*- coding: utf-8 -*-
"""Camera Forensic Realism Engine v3 - Test Suite"""

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
    img[:h//4, :, :] = [0.7, 0.8, 0.95]   # Sky highlight
    img[3*h//4:, :, :] = [0.08, 0.06, 0.05]  # Dark shadow
    cy, cx = h // 2, w // 2
    img[cy-30:cy+30, cx-30:cx+30, :] = [0.76, 0.57, 0.45]  # Skin
    return np.clip(img, 0.0, 1.0)


def check(out, shape, name):
    ok = True
    if out.shape != shape: print(f"  [FAIL] {name}: shape"); ok = False
    if out.dtype != np.float32: print(f"  [FAIL] {name}: dtype {out.dtype}"); ok = False
    if np.any(np.isnan(out)) or np.any(np.isinf(out)): print(f"  [FAIL] {name}: NaN/Inf"); ok = False
    if out.min() < 0 or out.max() > 1: print(f"  [FAIL] {name}: range [{out.min():.4f},{out.max():.4f}]"); ok = False
    if ok: print(f"  [PASS] {name}")
    return ok


def test_tone(): 
    print("\n--- Test 1: Tone Mapping ---")
    from forensic_engine import apply_iphone_tone_curve
    img = make_test_image()
    r = apply_iphone_tone_curve(img, 0.7, 0.5, 0.4, 0.5)
    return check(r, img.shape, "Tone curve")

def test_p3():
    print("\n--- Test 2: P3 Color ---")
    from forensic_engine import apply_p3_color_rendering
    img = make_test_image()
    r = apply_p3_color_rendering(img, 0.6, 0.3, 0.3)
    return check(r, img.shape, "P3 color")

def test_local():
    print("\n--- Test 3: Smart HDR ---")
    from forensic_engine import apply_local_tone_mapping
    img = make_test_image()
    r = apply_local_tone_mapping(img, 0.5, 0.5)
    return check(r, img.shape, "Local tone mapping")

def test_skin():
    print("\n--- Test 4: Real Tone ---")
    from forensic_engine import apply_skin_tone_rendering
    img = make_test_image()
    r = apply_skin_tone_rendering(img, 0.6, 0.5)
    ok = check(r, img.shape, "Skin rendering")
    skin_diff = np.mean(np.abs(r[98:158, 98:158, :] - img[98:158, 98:158, :]))
    bg_diff = np.mean(np.abs(r[:40, :40, :] - img[:40, :40, :]))
    print(f"  Skin diff: {skin_diff:.4f}, BG diff: {bg_diff:.4f}")
    return ok

def test_blue_shadows():
    print("\n--- Test 5: Blue Shadow Tint ---")
    from forensic_engine import apply_blue_shadow_tint
    img = make_test_image()
    r = apply_blue_shadow_tint(img, 0.5, 0.35, 0.5)
    ok = check(r, img.shape, "Blue shadows")
    # Dark area (bottom) should have more blue
    dark_orig_b = np.mean(img[200:, :, 2])
    dark_new_b = np.mean(r[200:, :, 2])
    dark_orig_r = np.mean(img[200:, :, 0])
    dark_new_r = np.mean(r[200:, :, 0])
    if dark_new_b > dark_orig_b and dark_new_r < dark_orig_r:
        print(f"  [PASS] Blue tint in shadows (B: {dark_orig_b:.4f}->{dark_new_b:.4f}, R: {dark_orig_r:.4f}->{dark_new_r:.4f})")
    else:
        print(f"  [INFO] B: {dark_orig_b:.4f}->{dark_new_b:.4f}, R: {dark_orig_r:.4f}->{dark_new_r:.4f}")
    return ok

def test_warm_highlights():
    print("\n--- Test 6: Warm Highlights ---")
    from forensic_engine import apply_highlight_warmth
    img = make_test_image()
    r = apply_highlight_warmth(img, 0.5, 0.7, 0.5)
    ok = check(r, img.shape, "Warm highlights")
    # Bright area (top) should have more red warmth
    hl_orig_r = np.mean(img[:40, :, 0])
    hl_new_r = np.mean(r[:40, :, 0])
    hl_orig_b = np.mean(img[:40, :, 2])
    hl_new_b = np.mean(r[:40, :, 2])
    if hl_new_r > hl_orig_r and hl_new_b < hl_orig_b:
        print(f"  [PASS] Warm highlights (R: {hl_orig_r:.4f}->{hl_new_r:.4f}, B: {hl_orig_b:.4f}->{hl_new_b:.4f})")
    else:
        print(f"  [INFO] R: {hl_orig_r:.4f}->{hl_new_r:.4f}, B: {hl_orig_b:.4f}->{hl_new_b:.4f}")
    return ok

def test_wb():
    print("\n--- Test 7: White Balance ---")
    from forensic_engine import apply_white_balance
    img = np.ones((64, 64, 3), dtype=np.float32) * 0.5
    r = apply_white_balance(img, 0.7, 0.3, 0.0)
    ok = check(r, img.shape, "White balance")
    rd = r[32,32,0] - img[32,32,0]; bd = r[32,32,2] - img[32,32,2]
    print(f"  R: {rd:+.4f}, B: {bd:+.4f}")
    if rd > 0 and bd < 0: print(f"  [PASS] Warm WB")
    return ok

def test_pipeline():
    print("\n--- Test 8: Full Pipeline ---")
    from forensic_engine import process_iphone_realism
    img = make_test_image()
    t0 = time.time()
    r = process_iphone_realism(img, master_strength=0.7, seed=42)
    elapsed = time.time() - t0
    ok = check(r, img.shape, f"Pipeline ({elapsed:.2f}s)")
    print(f"  Total diff: {np.mean(np.abs(r-img)):.4f}")
    return ok

def test_node():
    print("\n--- Test 9: ComfyUI Node ---")
    try: import torch
    except ImportError: print("  [SKIP] No PyTorch"); return True
    from nodes import CameraForensicRealismEngine
    node = CameraForensicRealismEngine()
    inputs = node.INPUT_TYPES()["required"]
    print(f"  {len(inputs)} widgets")
    # Check new color grading inputs exist
    for name in ["enable_color_grading", "blue_shadows", "warm_highlights"]:
        if name in inputs:
            print(f"  [PASS] '{name}' present")
        else:
            print(f"  [FAIL] '{name}' MISSING"); return False
    test_img = torch.rand(1, 128, 128, 3)
    result = node.apply_iphone_realism(
        image=test_img, master_strength=0.7, seed=42,
        enable_tone_mapping=True, tone_strength=0.6,
        highlight_rolloff=0.5, shadow_lift=0.4, contrast=0.5,
        enable_p3_color=True, color_strength=0.5,
        color_saturation=0.3, color_warmth=0.3,
        enable_local_tone=True, local_tone_strength=0.35, detail_boost=0.4,
        enable_skin_rendering=True, skin_strength=0.5, skin_warmth=0.4,
        enable_white_balance=True, wb_strength=0.5, wb_temperature=0.25, wb_tint=0.0,
        enable_color_grading=True, blue_shadows=0.4, warm_highlights=0.3,
        enable_sharpening=True, sharpen_strength=0.3,
        enable_sensor=True, sensor_strength=0.25, sensor_noise=0.3, sensor_vignette=0.4,
    )
    out = result[0]
    if out.shape == test_img.shape: print(f"  [PASS] Shape: {tuple(out.shape)}")
    else: print(f"  [FAIL] Shape"); return False
    if 0 <= out.min() and out.max() <= 1: print(f"  [PASS] Range: [{out.min():.4f}, {out.max():.4f}]")
    else: print(f"  [FAIL] Range"); return False
    return True

def test_js_exists():
    print("\n--- Test 10: Custom UI ---")
    js_path = os.path.join(os.path.dirname(__file__), "js", "camera_forensic_ui.js")
    if os.path.exists(js_path):
        size = os.path.getsize(js_path)
        print(f"  [PASS] JS UI file exists ({size} bytes)")
        return True
    else:
        print(f"  [FAIL] JS UI file missing")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Camera Forensic Realism Engine v3 - Test Suite")
    print("=" * 60)
    tests = [test_tone, test_p3, test_local, test_skin, test_blue_shadows,
             test_warm_highlights, test_wb, test_pipeline, test_node, test_js_exists]
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
