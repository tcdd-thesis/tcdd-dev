#!/usr/bin/env python3
"""
Quick script to show what classes are in your model
"""
from ultralytics import YOLO
import sys

if len(sys.argv) > 1:
    model_path = sys.argv[1]
else:
    model_path = "backend/python/model/v0-20250827.1a.pt"

try:
    model = YOLO(model_path)
    print(f"\nModel: {model_path}")
    print(f"Number of classes: {len(model.names)}")
    print(f"\nClass names (from model):")
    for idx, name in model.names.items():
        print(f"  {idx}: {name}")
except Exception as e:
    print(f"Error loading model: {e}")
