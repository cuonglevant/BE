#!/usr/bin/env python3
"""
Quick system verification before starting server
"""
import sys
from pathlib import Path

print("=" * 70)
print("SYSTEM VERIFICATION")
print("=" * 70)

# Check Python version
print(f"\n✓ Python version: {sys.version.split()[0]}")

# Check dependencies
print("\nChecking dependencies...")
try:
    import flask
    print(f"  ✓ flask {flask.__version__}")
except ImportError:
    print("  ✗ flask not installed")
    sys.exit(1)

try:
    import pymongo
    print(f"  ✓ pymongo {pymongo.__version__}")
except ImportError:
    print("  ✗ pymongo not installed")
    sys.exit(1)

try:
    import cv2
    print(f"  ✓ opencv {cv2.__version__}")
except ImportError:
    print("  ✗ opencv not installed")
    sys.exit(1)

try:
    import numpy
    print(f"  ✓ numpy {numpy.__version__}")
except ImportError:
    print("  ✗ numpy not installed")
    sys.exit(1)

# Check key files exist
print("\nChecking key files...")
required_files = [
    "main.py",
    "requirements.txt",
    ".env",
    "services/Process/balanced_grid_omr.py",
    "services/Process/balanced_grid_p2.py",
    "services/Process/balanced_grid_p3.py",
    "services/Grade/create_ans.py"
]

for file in required_files:
    path = Path(file)
    if path.exists():
        print(f"  ✓ {file}")
    else:
        print(f"  ✗ {file} - NOT FOUND")
        sys.exit(1)

# Check test images
print("\nChecking test images...")
image_dir = Path("2912")
if image_dir.exists():
    images = list(image_dir.glob("*.jpg"))
    print(f"  ✓ Found {len(images)} test images in 2912/")
else:
    print("  ⚠ 2912/ folder not found (optional)")

# Check validation data
validation_file = Path("validation_clean/validation_results.json")
if validation_file.exists():
    print("  ✓ Validation data found")
else:
    print("  ⚠ Validation data not found (optional)")

print("\n" + "=" * 70)
print("✅ SYSTEM READY!")
print("=" * 70)
print("\nTo start the server, run:")
print("  python main.py")
print("\nAPI will be available at:")
print("  http://localhost:5000")
print("\nAPI documentation:")
print("  http://localhost:5000/docs")
print("=" * 70)
