import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform
from .accuracy_improvements import AccuracyImprover


def process_p1_answers(image_path=None, show_images=False, save_images=False, enable_ocr_validation=False):
    """
    Process PHẦN I - Standard ABCD multiple choice (40 questions)
    
    Args:
        image_path: Path to image file
        show_images: Display images (disabled for server)
        save_images: Save processed images
        enable_ocr_validation: Enable OCR validation for question numbers
    
    Returns:
        dict: {'answers': [(question_num, answer), ...], 'validation': validation_results}
        e.g., {'answers': [(1, 'A'), (2, 'B'), ...], 'validation': {...}}
    """
    show_images = False
    
    if image_path is None:
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p12.jpg")
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Cannot read image: {image_path}")
        return []
    
    # Initialize accuracy improver
    improver = AccuracyImprover()
    
    # Use original image for contour detection (enhancement might affect edge detection)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)
    
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    # Find 4-corner contours for answer grids
    qualified_contours = []
    for i, contour in enumerate(contours):
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = cv2.contourArea(contour)
        
        if len(approx) == 4 and 150000 < area < 300000:
            qualified_contours.append((contour, approx, area, i))
    
    if len(qualified_contours) < 4:
        print(f"Warning: Found only {len(qualified_contours)} answer grids, expected 4")
    
    # Sort by vertical position
    qualified_contours.sort(key=lambda x: cv2.boundingRect(x[0])[1])
    
    all_answers = {}
    
    # Process each contour (4 grids = 4x10 questions)
    for idx, (contour, approx, area, original_idx) in enumerate(qualified_contours[:4]):
        paper_points = approx.reshape(4, 2)
        cropped_paper = four_point_transform(cv2.imread(image_path), paper_points)
        cropped_paper = cv2.rotate(cropped_paper, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # Apply enhancement to the cropped grid for better bubble detection
        cropped_paper = improver.enhance_image_quality(cropped_paper)
        
        height, width = cropped_paper.shape[:2]
        rows, cols = 11, 5  # 11 rows (1 header + 10 questions), 5 cols (1 number + ABCD)
        cell_height, cell_width = height // rows, width // cols
        
        # Apply thresholding to the enhanced grayscale image
        _, binary = cv2.threshold(cropped_paper, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Calculate threshold using enhanced method - use 65th percentile for better sensitivity
        mean_values = []
        for col in range(1, cols):
            for row in range(1, rows):
                y1, y2 = row * cell_height, (row + 1) * cell_height
                x1, x2 = col * cell_width, (col + 1) * cell_width
                cell = binary[y1:y2, x1:x2]
                mean_values.append(np.mean(cell))
        
        threshold = np.percentile(mean_values, 65)
        
        # Detect filled circles using enhanced methods
        col_to_answer = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
        question_offset = idx * 10  # Grid 0: Q1-10, Grid 1: Q11-20, etc.
        
        for row in range(1, rows):
            question_num = question_offset + row
            for col in range(1, cols):
                y1, y2 = row * cell_height, (row + 1) * cell_height
                x1, x2 = col * cell_width, (col + 1) * cell_width
                cell = binary[y1:y2, x1:x2]
                mean_val = np.mean(cell)
                
                # Use the calculated threshold for better sensitivity
                if mean_val < threshold:
                    answer = col_to_answer[col]
                    all_answers[question_num] = answer
                    break  # Only one answer per question
    
    # Return sorted list
    result_answers = []
    for q in range(1, 41):
        result_answers.append((q, all_answers.get(q, '')))
    
    # OCR validation if enabled
    validation_results = None
    if enable_ocr_validation:
        try:
            validation_results = improver.validate_p1_answers_with_ocr(
                cv2.imread(image_path), result_answers
            )
        except Exception as e:
            print(f"OCR validation failed: {e}")
            validation_results = {'error': str(e)}
    
    return {
        'answers': result_answers,
        'validation': validation_results
    }
