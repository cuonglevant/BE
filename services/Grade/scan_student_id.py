from services.Process.ec import process_exam_code
from services.Process.p1 import process_p1_answers
from services.Process.p2 import process_p2_answers
from services.Process.p3 import process_p3_answers

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
    return process_p1_answers(image_path, show_images, save_images)


def scan_p2(image_path=None, show_images=False, save_images=False):
    return process_p2_answers(image_path, show_images, save_images)


def scan_p3(image_path=None, show_images=False, save_images=False):
    return process_p3_answers(image_path, show_images, save_images)

