#!/usr/bin/env python3
"""
Quick test script to verify camera and YOLOv8 setup
Run this before deploying to make sure everything works
"""
import sys
import cv2

def test_opencv():
    """Test OpenCV installation"""
    print("Testing OpenCV...")
    try:
        print(f"  OpenCV version: {cv2.__version__}")
        print("  ✓ OpenCV installed")
        return True
    except Exception as e:
        print(f"  ✗ OpenCV error: {e}")
        return False

def test_camera():
    """Test camera access"""
    print("\nTesting camera...")
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print(f"  Frame size: {frame.shape}")
                print("  ✓ Camera working")
                return True
            else:
                print("  ✗ Could not read frame")
                return False
        else:
            print("  ✗ Could not open camera")
            return False
    except Exception as e:
        print(f"  ✗ Camera error: {e}")
        return False

def test_yolo():
    """Test YOLOv8 installation"""
    print("\nTesting YOLOv8...")
    try:
        from ultralytics import YOLO
        print("  ✓ ultralytics installed")
        
        # Try loading a model
        try:
            model = YOLO('yolov8n.pt')
            print(f"  Model classes: {len(model.names)}")
            print("  ✓ YOLOv8 model loaded")
            return True
        except Exception as e:
            print(f"  ✗ Model loading error: {e}")
            return False
    except ImportError:
        print("  ✗ ultralytics not installed")
        return False

def test_picamera():
    """Test Raspberry Pi camera (optional)"""
    print("\nTesting Raspberry Pi camera...")
    try:
        from picamera2 import Picamera2
        print("  ✓ picamera2 installed")
        try:
            picam = Picamera2()
            config = picam.create_preview_configuration(main={"size": (640, 480)})
            picam.configure(config)
            print("  ✓ Pi camera configured")
            return True
        except Exception as e:
            print(f"  ⚠ Pi camera error (this is OK if not on Pi): {e}")
            return False
    except ImportError:
        print("  ⚠ picamera2 not installed (OK if not on Raspberry Pi)")
        return False

def test_flask():
    """Test Flask installation"""
    print("\nTesting Flask...")
    try:
        import flask
        print(f"  Flask version: {flask.__version__}")
        print("  ✓ Flask installed")
        return True
    except ImportError:
        print("  ✗ Flask not installed")
        return False

def main():
    print("=" * 50)
    print("Sign Detection System - Pre-deployment Test")
    print("=" * 50)
    
    results = {
        'OpenCV': test_opencv(),
        'Camera': test_camera(),
        'YOLOv8': test_yolo(),
        'PiCamera': test_picamera(),
        'Flask': test_flask()
    }
    
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for component, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{component:15} {status}")
    
    critical_tests = ['OpenCV', 'Camera', 'Flask']
    critical_passed = all(results[test] for test in critical_tests if test in results)
    
    print("\n" + "=" * 50)
    if critical_passed:
        print("✓ All critical tests passed!")
        print("You can proceed with deployment.")
        if not results.get('YOLOv8', False):
            print("\n⚠ Warning: YOLOv8 test failed. Install with:")
            print("  pip install ultralytics")
        return 0
    else:
        print("✗ Some critical tests failed.")
        print("Please fix the issues before deploying.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
