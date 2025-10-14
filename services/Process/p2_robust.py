"""
Robust P2 (True/False) Processing
Uses advanced preprocessing and contour-based detection
"""
import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform  # noqa: E402
from .robust_preprocessing import RobustPreprocessor  # noqa: E402


def calculate_cell_fill(cell):
    """Calculate how filled a cell is (0-1)"""
    if cell.size == 0:
        return 0.0
    
    # For inverted binary images, white = filled
    filled_pixels = np.sum(cell == 255)
    total_pixels = cell.size
    
    return filled_pixels / total_pixels if total_pixels > 0 else 0.0


def process_p2_answers_robust(image_path=None, show_images=False):
    """
    Robust processing of PHẦN II - True/False (8 questions, 4 parts each)
    
    Returns:
        dict: {question_num: {'a': bool, 'b': bool, 'c': bool, 'd': bool}}
    """
    if image_path is None:
        image_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "p23.jpg")
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Cannot read image: {image_path}")
        return {}
    
    # Initialize robust preprocessor
    preprocessor = RobustPreprocessor()
    
    # Apply aggressive preprocessing for P2
    enhanced = preprocessor.enhance_for_bubble_detection(
        image, aggressive=True)
    
    # Find contours using robust method with wider area range
    qualified_contours = preprocessor.find_contours_robust(
        enhanced,
        min_area=30000,  # Lower bound for P2
        max_area=200000  # Upper bound for P2
    )
    
    # Fallback to traditional method
    if not qualified_contours:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        
        contours, _ = cv2.findContours(
            edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            area = cv2.contourArea(contour)
            
            if len(approx) == 4 and 30000 < area < 200000:
                qualified_contours.append((contour, approx, area))
    
    if not qualified_contours:
        print("No PHẦN II cells found")
        return {}
    
    p2_answers = {}
    
    # Process each contour
    for contour, approx, area, *rest in qualified_contours:
        try:
            paper_points = approx.reshape(4, 2)
            cropped_paper = four_point_transform(
                cv2.imread(image_path), paper_points)
            
            # Preprocess cropped region
            if len(cropped_paper.shape) == 3:
                cropped_gray = cv2.cvtColor(
                    cropped_paper, cv2.COLOR_BGR2GRAY)
            else:
                cropped_gray = cropped_paper
            
            cropped_enhanced = preprocessor.adaptive_enhance(cropped_gray)
            
            # Apply thresholding
            _, binary = cv2.threshold(
                cropped_enhanced, 0, 255,
                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            height, width = binary.shape[:2]
            
            # Detect grid structure
            # P2 has varied layouts, try to detect automatically
            rows = 9  # 1 header + 8 questions
            cols = 5  # 1 question number + 4 answer columns (a,b,c,d)
            
            cell_height = height // rows
            cell_width = width // cols
            
            # Process each question row
            for row in range(1, rows):
                question_num = row
                
                # Calculate fill for each column
                column_fills = {}
                
                for col in range(1, cols):  # Skip first column (question num)
                    padding_v = max(2, cell_height // 10)
                    padding_h = max(2, cell_width // 10)
                    
                    y1 = row * cell_height + padding_v
                    y2 = (row + 1) * cell_height - padding_v
                    x1 = col * cell_width + padding_h
                    x2 = (col + 1) * cell_width - padding_h
                    
                    cell = binary[y1:y2, x1:x2]
                    
                    if cell.size == 0:
                        column_fills[col] = 0.0
                        continue
                    
                    fill = calculate_cell_fill(cell)
                    column_fills[col] = fill
                
                # Map columns to parts
                col_to_part = {1: 'a', 2: 'b', 3: 'c', 4: 'd'}
                
                # Determine threshold dynamically
                all_fills = list(column_fills.values())
                if all_fills:
                    threshold = np.percentile(all_fills, 60)
                    threshold = max(threshold, 0.15)  # Minimum 15%
                else:
                    threshold = 0.15
                
                # Store answers (INVERT: filled bubble = False in this exam format)
                answer_dict = {}
                for col, part in col_to_part.items():
                    if col in column_fills:
                        # Invert logic: high fill means False (empty means True)
                        answer_dict[part] = column_fills[col] <= threshold
                    else:
                        answer_dict[part] = True  # Missing = True (not filled)
                
                if question_num not in p2_answers:
                    p2_answers[question_num] = answer_dict
        
        except Exception as e:
            print(f"Error processing P2 contour: {e}")
            continue
    
    return p2_answers


# Alias for compatibility
process_p2_answers = process_p2_answers_robust
