#!/usr/bin/env python3
"""
Balanced Grid Smoke Test
Runs P1, P2, P3 balanced-grid processors on sample images in the 2912 folder
and prints concise summaries, including accuracy when validation data exists.
"""
import os
import sys

# Ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from services.Process.balanced_grid_omr import BalancedGridOMR
from services.Process.balanced_grid_p2 import BalancedGridP2
from services.Process.balanced_grid_p3 import BalancedGridP3


def run_p1(image_path: str):
    print("\n=== P1 (ABCD) balanced-grid test ===")
    omr = BalancedGridOMR()
    result = omr.process_part1(image_path)
    print(f"P1: detected={result.get('total_detected', 0)}/40, accuracy={result.get('accuracy', 0.0):.1f}%")
    return result


def run_p2(image_path: str):
    print("\n=== P2 (True/False) balanced-grid test ===")
    p2 = BalancedGridP2()
    result = p2.process_part2(image_path)
    print(
        f"P2: questions={result.get('total_detected', 0)}/8, "
        f"options={result.get('total_options', 0)}, "
        f"correct={result.get('correct_count', 0)}, "
        f"accuracy={result.get('accuracy', 0.0):.1f}%"
    )
    return result


def run_p3(image_path: str):
    print("\n=== P3 (Decimal) balanced-grid test ===")
    p3 = BalancedGridP3(debug_mode=True)
    result = p3.process_part3(image_path)
    print(
        f"P3: detected={result.get('total_detected', 0)}/8, "
        f"accuracy={result.get('accuracy', 0.0):.1f}%"
    )
    return result


def main():
    p1_p2_img = os.path.join(ROOT, '2912', 'p12_1.jpg')
    p3_img = os.path.join(ROOT, '2912', 'p23_4.jpg')

    if not os.path.exists(p1_p2_img):
        print(f"ERROR: Missing image {p1_p2_img}")
        return 1
    if not os.path.exists(p3_img):
        print(f"ERROR: Missing image {p3_img}")
        return 1

    p1 = run_p1(p1_p2_img)
    p2 = run_p2(p1_p2_img)
    p3 = run_p3(p3_img)

    print("\n=== SUMMARY ===")
    print(
        f"P1: detected {p1.get('total_detected', 0)}/40, accuracy {p1.get('accuracy', 0.0):.1f}%\n"
        f"P2: questions {p2.get('total_detected', 0)}/8, options {p2.get('total_options', 0)}, "
        f"correct {p2.get('correct_count', 0)}, accuracy {p2.get('accuracy', 0.0):.1f}%\n"
        f"P3: detected {p3.get('total_detected', 0)}/8, accuracy {p3.get('accuracy', 0.0):.1f}%"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
