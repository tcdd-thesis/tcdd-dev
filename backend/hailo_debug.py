#!/usr/bin/env python3
"""
Hailo pybind11 / HailoRT Debug Script
======================================
Run this directly on the Raspberry Pi 5 to diagnose the "passed size - 0"
error when calling InputVStream.send() or InferVStreams.infer().

Usage:
    python3 hailo_debug.py <path_to_model.hef>

    Example:
    python3 hailo_debug.py backend/models/yolov8n.hef
"""

import sys
import os
import ctypes
import struct
import platform
import traceback
import time
import numpy as np

# ─── Formatting helpers ──────────────────────────────────────────────────────

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[94m[INFO]\033[0m"
SECT = "\033[96m"
RESET = "\033[0m"

def section(title):
    print(f"\n{'=' * 70}")
    print(f"{SECT}  {title}{RESET}")
    print(f"{'=' * 70}")

def kv(key, value):
    print(f"  {key:.<40s} {value}")

# ─── 1. Environment ─────────────────────────────────────────────────────────

section("1. ENVIRONMENT")

kv("Python version", sys.version.replace('\n', ' '))
kv("Platform", platform.platform())
kv("Machine", platform.machine())
kv("Pointer size (bits)", str(struct.calcsize("P") * 8))

# numpy
kv("numpy version", np.__version__)

# pybind11
try:
    import pybind11
    kv("pybind11 version (Python pkg)", pybind11.__version__)
except ImportError:
    kv("pybind11 version (Python pkg)", "NOT INSTALLED (pip package)")

# hailo_platform
try:
    import hailo_platform
    kv("hailo_platform version", getattr(hailo_platform, '__version__', 'attr missing'))
except ImportError:
    print(f"  {FAIL} hailo_platform is NOT importable. Cannot continue.")
    sys.exit(1)

# _pyhailort native module
try:
    from hailo_platform import _pyhailort
    mod_file = getattr(_pyhailort, '__file__', 'unknown')
    kv("_pyhailort native lib", mod_file)
except Exception as e:
    kv("_pyhailort native lib", f"IMPORT ERROR: {e}")

# libhailort.so
try:
    libhailort = ctypes.CDLL("libhailort.so", mode=ctypes.RTLD_GLOBAL)
    kv("libhailort.so", "loaded OK")
except OSError as e:
    try:
        libhailort = ctypes.CDLL("libhailort.so.4", mode=ctypes.RTLD_GLOBAL)
        kv("libhailort.so.4", "loaded OK")
    except OSError as e2:
        kv("libhailort.so", f"NOT FOUND: {e2}")
        libhailort = None

# hailortcli
import shutil
cli = shutil.which("hailortcli")
kv("hailortcli", cli or "NOT FOUND")

# ─── 2. pybind11 numpy array probe ──────────────────────────────────────────

section("2. PYBIND11 NUMPY ARRAY PROBE (pure Python / ctypes)")

print("""
  This test checks whether numpy arrays maintain valid buffer metadata
  when passed through common patterns that mimic pybind11 conversion.
""")

# Test: basic array properties via ctypes
test_shapes = [
    (1, 640, 640, 3),   # standard YOLO batch
    (640, 640, 3),       # single frame, no batch dim
]

for shape in test_shapes:
    arr = np.zeros(shape, dtype=np.uint8)
    arr_c = np.ascontiguousarray(arr)
    ptr = arr_c.ctypes.data
    nbytes = arr_c.nbytes
    expected = int(np.prod(shape))

    ok = nbytes == expected and ptr != 0
    tag = PASS if ok else FAIL
    print(f"  {tag} shape={shape}  nbytes={nbytes} (expected {expected})  "
          f"ptr=0x{ptr:016x}  contiguous={arr_c.flags['C_CONTIGUOUS']}")

# Test: does np.expand_dims create a valid view?
frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
frame_c = np.ascontiguousarray(frame)
batch = np.expand_dims(frame_c, axis=0)
ptr_frame = frame_c.ctypes.data
ptr_batch = batch.ctypes.data
shares = np.shares_memory(frame_c, batch)
print(f"\n  expand_dims sharing test:")
print(f"    frame  ptr=0x{ptr_frame:016x}  nbytes={frame_c.nbytes}")
print(f"    batch  ptr=0x{ptr_batch:016x}  nbytes={batch.nbytes}")
print(f"    shares_memory={shares}  same_ptr={ptr_frame == ptr_batch}")
if ptr_frame == ptr_batch and batch.nbytes == 1228800:
    print(f"    {PASS} expand_dims produces valid view")
else:
    print(f"    {WARN} expand_dims pointers differ (may indicate copy)")

# ─── 3. _pyhailort C++ binding introspection ────────────────────────────────

section("3. _pyhailort C++ BINDING INTROSPECTION")

try:
    from hailo_platform import _pyhailort

    # List relevant classes / methods
    interesting = ['InputVStream', 'OutputVStream', 'InferVStreams',
                   'VDevice', 'ConfiguredNetwork', 'HEF',
                   'InputVStreamWrapper', 'OutputVStreamWrapper']

    found_classes = []
    for name in dir(_pyhailort):
        obj = getattr(_pyhailort, name)
        if isinstance(obj, type):
            for target in interesting:
                if target.lower() in name.lower():
                    found_classes.append((name, obj))
                    break

    for cls_name, cls_obj in found_classes:
        methods = [m for m in dir(cls_obj) if not m.startswith('_')]
        print(f"  {cls_name}:")
        for m in methods:
            mobj = getattr(cls_obj, m, None)
            doc = (getattr(mobj, '__doc__', '') or '')[:120].replace('\n', ' ')
            print(f"    .{m}()  {doc}")
        print()

    # Check if send/write exist directly
    for wrapper_name in ['InputVStream', 'InputVStreamWrapper']:
        cls = getattr(_pyhailort, wrapper_name, None)
        if cls is None:
            continue
        has_send = hasattr(cls, 'send')
        has_write = hasattr(cls, 'write')
        has_set_buf = hasattr(cls, 'set_buffer')
        print(f"  {wrapper_name}: send={has_send}  write={has_write}  set_buffer={has_set_buf}")

        # Check the write/send signature (from pybind11 docstring)
        for method_name in ['send', 'write']:
            method = getattr(cls, method_name, None)
            if method:
                doc = getattr(method, '__doc__', 'no doc')
                print(f"    {method_name} docstring: {doc[:200]}")

except Exception as e:
    print(f"  {FAIL} Could not introspect _pyhailort: {e}")
    traceback.print_exc()

# ─── 4. HEF model loading & vstream creation ────────────────────────────────

section("4. HEF MODEL LOADING & VSTREAM CREATION")

if len(sys.argv) < 2:
    print(f"  {WARN} No HEF path provided. Skipping tests 4-7.")
    print(f"  Usage: python3 {sys.argv[0]} <path_to_model.hef>")
    sys.exit(0)

hef_path = sys.argv[1]
if not os.path.exists(hef_path):
    print(f"  {FAIL} HEF file not found: {hef_path}")
    sys.exit(1)

kv("HEF path", hef_path)
kv("HEF size", f"{os.path.getsize(hef_path):,} bytes")

from hailo_platform import (
    HEF, VDevice, HailoStreamInterface,
    ConfigureParams,
    InputVStreams, OutputVStreams,
    InputVStreamParams, OutputVStreamParams
)

# Also try importing InferVStreams for comparison test
try:
    from hailo_platform import InferVStreams
    HAS_INFER_VSTREAMS = True
except ImportError:
    HAS_INFER_VSTREAMS = False

vdevice = None
network_group = None
input_vstreams_ctx = None
output_vstreams_ctx = None
activation_ctx = None

try:
    vdevice = VDevice()
    print(f"  {PASS} VDevice created")

    hef = HEF(hef_path)
    print(f"  {PASS} HEF loaded")

    configure_params = ConfigureParams.create_from_hef(
        hef, interface=HailoStreamInterface.PCIe)
    network_groups = vdevice.configure(hef, configure_params)
    network_group = network_groups[0]
    print(f"  {PASS} Network configured: {network_group.name if hasattr(network_group, 'name') else '?'}")

    # Inspect input/output info
    input_vstream_info = hef.get_input_vstream_infos()
    output_vstream_info = hef.get_output_vstream_infos()

    print(f"\n  Input vstreams ({len(input_vstream_info)}):")
    for info in input_vstream_info:
        name = info.name if hasattr(info, 'name') else str(info)
        shape = info.shape if hasattr(info, 'shape') else 'N/A'
        fmt = info.format if hasattr(info, 'format') else 'N/A'
        print(f"    name={name}  shape={shape}  format={fmt}")

    print(f"\n  Output vstreams ({len(output_vstream_info)}):")
    for info in output_vstream_info:
        name = info.name if hasattr(info, 'name') else str(info)
        shape = info.shape if hasattr(info, 'shape') else 'N/A'
        fmt = info.format if hasattr(info, 'format') else 'N/A'
        print(f"    name={name}  shape={shape}  format={fmt}")

    input_params = InputVStreamParams.make(network_group)
    output_params = OutputVStreamParams.make(network_group)
    input_names = list(input_params.keys())
    print(f"\n  {PASS} VStream params created. Input names: {input_names}")

except Exception as e:
    print(f"  {FAIL} Setup failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# ─── 5. Test: send() with various buffer strategies ─────────────────────────

section("5. SEND/RECV TEST — various buffer strategies")

test_results = {}

def run_send_test(test_name, make_buffer_fn, single_activation=True):
    """Run a single send/recv cycle and report result."""
    global network_group

    print(f"\n  --- Test: {test_name} ---")
    _input_ctx = None
    _output_ctx = None
    _act_ctx = None

    try:
        # Create fresh vstreams for each test
        inp_params = InputVStreamParams.make(network_group)
        out_params = OutputVStreamParams.make(network_group)

        _input_ctx = InputVStreams(network_group, inp_params)
        _output_ctx = OutputVStreams(network_group, out_params)
        input_vs = _input_ctx.__enter__()
        output_vs = _output_ctx.__enter__()

        if single_activation:
            _act_ctx = network_group.activate()
            _act_ctx.__enter__()

        input_vstream = input_vs.get(input_names[0])

        # Create the buffer
        buf = make_buffer_fn()
        print(f"    buffer: shape={buf.shape}  dtype={buf.dtype}  "
              f"nbytes={buf.nbytes}  contiguous={buf.flags['C_CONTIGUOUS']}  "
              f"ptr=0x{buf.ctypes.data:016x}")

        if buf.nbytes == 0:
            print(f"    {FAIL} Buffer has 0 bytes BEFORE send!")
            test_results[test_name] = "FAIL (0 bytes before send)"
            return

        # Attempt send
        t0 = time.monotonic()
        input_vstream.send(buf)
        t_send = time.monotonic() - t0
        print(f"    {PASS} send() completed in {t_send*1000:.1f}ms")

        # Attempt recv (with short timeout awareness)
        for ovs in output_vs:
            t0 = time.monotonic()
            result = ovs.recv()
            t_recv = time.monotonic() - t0
            result_type = type(result).__name__
            if isinstance(result, list):
                print(f"    {PASS} recv() returned list[{len(result)}] in {t_recv*1000:.1f}ms")
            elif isinstance(result, np.ndarray):
                print(f"    {PASS} recv() returned ndarray shape={result.shape} in {t_recv*1000:.1f}ms")
            else:
                print(f"    {INFO} recv() returned {result_type} in {t_recv*1000:.1f}ms")

        test_results[test_name] = "PASS"

    except Exception as e:
        err_str = str(e)
        print(f"    {FAIL} Exception: {err_str}")
        # Check if the error is the known 0-byte issue
        if "size" in err_str.lower() and "0" in err_str:
            print(f"    ^ This IS the known 0-byte buffer bug")
        test_results[test_name] = f"FAIL ({err_str[:80]})"

    finally:
        # Teardown
        if _act_ctx is not None:
            try:
                _act_ctx.__exit__(None, None, None)
            except Exception:
                pass
        if _output_ctx is not None:
            try:
                _output_ctx.__exit__(None, None, None)
            except Exception:
                pass
        if _input_ctx is not None:
            try:
                _input_ctx.__exit__(None, None, None)
            except Exception:
                pass

# --- Test A: Fresh array (current code pattern) ---
def make_fresh_array():
    frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    frame_c = np.ascontiguousarray(frame)
    batch = np.expand_dims(frame_c, axis=0)
    return batch

run_send_test("A: fresh array + expand_dims", make_fresh_array)

# --- Test B: Pre-allocated persistent buffer (Option 4) ---
_persistent_buf = np.zeros((1, 640, 640, 3), dtype=np.uint8)

def make_preallocated():
    frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    np.copyto(_persistent_buf[0], frame)
    return _persistent_buf

run_send_test("B: pre-allocated + np.copyto", make_preallocated)

# --- Test C: Single contiguous array, no expand_dims ---
def make_flat_batch():
    batch = np.random.randint(0, 255, (1, 640, 640, 3), dtype=np.uint8)
    return np.ascontiguousarray(batch)

run_send_test("C: direct (1,640,640,3) allocation", make_flat_batch)

# --- Test D: Without explicit activation (test double-activation theory) ---
def make_fresh_noact():
    return np.random.randint(0, 255, (1, 640, 640, 3), dtype=np.uint8)

run_send_test("D: no explicit activation", make_fresh_noact, single_activation=False)

# --- Test E: np.copy to force owned buffer ---
def make_copy():
    frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    batch = np.expand_dims(frame, axis=0)
    return np.copy(batch)   # force a new allocation that owns its data

run_send_test("E: np.copy (force owned data)", make_copy)

# --- Test F: fromstring/frombuffer round-trip (new buffer identity) ---
def make_bytes_roundtrip():
    frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    raw = frame.tobytes()
    batch = np.frombuffer(raw, dtype=np.uint8).reshape(1, 640, 640, 3).copy()
    return batch

run_send_test("F: tobytes → frombuffer → copy", make_bytes_roundtrip)

# ─── 6. Test: InferVStreams.infer() for comparison ───────────────────────────

section("6. InferVStreams.infer() COMPARISON TEST")

if HAS_INFER_VSTREAMS:
    print(f"  InferVStreams is available, testing dict-based infer()...")
    _infer_ctx = None
    _act_ctx2 = None
    try:
        inp_params = InputVStreamParams.make(network_group)
        out_params = OutputVStreamParams.make(network_group)

        _act_ctx2 = network_group.activate()
        _act_ctx2.__enter__()

        _infer_ctx = InferVStreams(network_group, inp_params, out_params)
        pipeline = _infer_ctx.__enter__()

        input_data = np.random.randint(0, 255, (1, 640, 640, 3), dtype=np.uint8)
        input_dict = {input_names[0]: input_data}

        print(f"    input_dict['{input_names[0]}']: shape={input_data.shape}  "
              f"nbytes={input_data.nbytes}  ptr=0x{input_data.ctypes.data:016x}")

        t0 = time.monotonic()
        result = pipeline.infer(input_dict)
        t_infer = time.monotonic() - t0
        print(f"    {PASS} infer() completed in {t_infer*1000:.1f}ms")
        for k, v in result.items():
            if isinstance(v, list):
                print(f"    output '{k}': list[{len(v)}]")
            elif isinstance(v, np.ndarray):
                print(f"    output '{k}': ndarray shape={v.shape}")
            else:
                print(f"    output '{k}': {type(v).__name__}")
        test_results["InferVStreams.infer()"] = "PASS"

    except Exception as e:
        print(f"    {FAIL} infer() failed: {e}")
        test_results["InferVStreams.infer()"] = f"FAIL ({str(e)[:80]})"

    finally:
        if _infer_ctx:
            try:
                _infer_ctx.__exit__(None, None, None)
            except Exception:
                pass
        if _act_ctx2:
            try:
                _act_ctx2.__exit__(None, None, None)
            except Exception:
                pass
else:
    print(f"  {WARN} InferVStreams not importable, skipping.")

# ─── 7. Test: raw ctypes call to libhailort (bypass pybind11) ───────────────

section("7. RAW CTYPES PROBE — bypass pybind11 entirely")

print("""
  This test calls the HailoRT C library directly via ctypes to check if
  the buffer reaches C with the correct size when pybind11 is NOT involved.
  Note: this is a structural probe. Full inference via ctypes is complex
  and is covered in Option 1 of the fix plan.
""")

if libhailort is not None:
    try:
        # Probe: hailo_get_library_version
        get_ver = getattr(libhailort, 'hailo_get_library_version', None)
        if get_ver is not None:
            class HailoVersion(ctypes.Structure):
                _fields_ = [
                    ("major", ctypes.c_uint32),
                    ("minor", ctypes.c_uint32),
                    ("revision", ctypes.c_uint32),
                ]
            ver = HailoVersion()
            status = get_ver(ctypes.byref(ver))
            print(f"  hailo_get_library_version: {ver.major}.{ver.minor}.{ver.revision}  (status={status})")
        else:
            print(f"  {WARN} hailo_get_library_version not found in libhailort.so")

        # Demonstrate that a numpy buffer's ctypes pointer is valid and correct size
        buf = np.zeros((1, 640, 640, 3), dtype=np.uint8)
        c_ptr = buf.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        c_size = ctypes.c_size_t(buf.nbytes)
        print(f"  ctypes pointer test: ptr={ctypes.addressof(c_ptr.contents):#018x}  size={c_size.value}")
        if c_size.value == 1228800:
            print(f"  {PASS} ctypes gives correct size (1228800) — proves numpy buffer is valid")
            print(f"  {INFO} If send() fails but ctypes shows correct size, the bug is in pybind11 conversion")
        else:
            print(f"  {FAIL} Unexpected ctypes size: {c_size.value}")

    except Exception as e:
        print(f"  {FAIL} ctypes probe error: {e}")
        traceback.print_exc()
else:
    print(f"  {WARN} libhailort.so not loaded, skipping ctypes probe")

# ─── 8. Check pybind11 version compiled into _pyhailort ─────────────────────

section("8. PYBIND11 VERSION IN _pyhailort.so")

try:
    from hailo_platform import _pyhailort
    so_path = getattr(_pyhailort, '__file__', None)
    if so_path and os.path.exists(so_path):
        # Search for pybind11 version string embedded in the .so
        with open(so_path, 'rb') as f:
            data = f.read()

        # pybind11 embeds version as "pybind11 v2.X.Y" in the binary
        import re
        matches = re.findall(rb'pybind11[\s_]v?(\d+\.\d+\.\d+)', data)
        if matches:
            versions = list(set(m.decode() for m in matches))
            for v in versions:
                print(f"  {INFO} pybind11 version in binary: {v}")
                major, minor, patch = [int(x) for x in v.split('.')]
                if major == 2 and minor < 11:
                    print(f"  {WARN} pybind11 < 2.11 has known numpy buffer issues on ARM64!")
                    print(f"        Upgrading pybind11 and rebuilding _pyhailort may fix the bug.")
                elif major >= 2 and minor >= 11:
                    print(f"  {PASS} pybind11 >= 2.11 (numpy fixes included)")
        else:
            print(f"  {WARN} Could not find pybind11 version string in {so_path}")

        # Also search for the GIL-related pattern
        has_gil_scoped = b'gil_scoped_release' in data
        print(f"  GIL release in binary: {has_gil_scoped}")

    else:
        print(f"  {WARN} _pyhailort.__file__ not available")

except Exception as e:
    print(f"  {FAIL} Error: {e}")


# ─── 9. Summary ─────────────────────────────────────────────────────────────

section("9. SUMMARY")

all_pass = True
for name, result in test_results.items():
    tag = PASS if result == "PASS" else FAIL
    if result != "PASS":
        all_pass = False
    print(f"  {tag} {name}: {result}")

if all_pass:
    print(f"\n  {PASS} All tests passed! The 0-byte bug may be intermittent or")
    print(f"        triggered by specific conditions in the full app (threading, GC, etc.).")
    print(f"        Try running the full app with HAILORT_CONSOLE_LOGGER_LEVEL=info")
    print(f"        and check if the error appears at the SAME C++ location.")
elif any("PASS" in r for r in test_results.values()):
    passing = [k for k, v in test_results.items() if v == "PASS"]
    failing = [k for k, v in test_results.items() if v != "PASS"]
    print(f"\n  Some strategies work, others don't:")
    print(f"    Working: {', '.join(passing)}")
    print(f"    Broken:  {', '.join(failing)}")
    print(f"\n  {INFO} Use a working strategy in detector.py")
else:
    print(f"\n  {FAIL} ALL strategies fail — the bug is likely in the pybind11 layer")
    print(f"        or in HailoRT's internal buffer handling.")
    print(f"        Next steps:")
    print(f"        1. Check pybind11 version above — upgrade if < 2.11")
    print(f"        2. Try Option 1 (ctypes bypass) from the fix plan")
    print(f"        3. Try Option 2 (custom hailort build with buffer copy)")

print(f"\n  {INFO} hailort.log location: check /var/log/hailort.log or ~/.hailort/")
print(f"         Set HAILORT_CONSOLE_LOGGER_LEVEL=debug for console output")
print()

# Cleanup
try:
    if vdevice is not None:
        del vdevice
except Exception:
    pass
