from services.Process.ec import process_exam_code
from services.Process.balanced_grid_omr import BalancedGridOMR
from services.Process.balanced_grid_p2 import BalancedGridP2
from services.Process.balanced_grid_p3 import BalancedGridP3

def scan_student_id(image_path=None, show_images=False, save_images=False):
    """
    Scan student ID from image (currently uses exam_code logic as placeholder)
    In production, this should be replaced with proper student ID OCR
    """
    # TODO: Implement proper student ID scanning
    # For now, returns empty string or implement using exam_code logic
    return process_exam_code(image_path, show_images, save_images)

def scan_exam_code(image_path=None, show_images=False, save_images=False):
    return process_exam_code(image_path, show_images, save_images)


def scan_p1(image_path=None, show_images=False, save_images=False):
    omr = BalancedGridOMR()
    res = omr.process_part1(image_path)
    return [(a.get('question'), a.get('answer')) for a in (res.get('answers') or [])]


def scan_p2(image_path=None, show_images=False, save_images=False):
    p2 = BalancedGridP2()
    res = p2.process_part2(image_path)
    out = []
    for item in (res.get('answers') or []):
        q = item.get('question')
        for k, v in (item.get('answers') or {}).items():
            out.append((f"q{q}_{k}", bool(v)))
    return out


def scan_p3(image_path=None, show_images=False, save_images=False):
    p3 = BalancedGridP3(debug_mode=False)
    res = p3.process_part3(image_path)
    return [(a.get('question'), a.get('answer')) for a in (res.get('answers') or [])]

