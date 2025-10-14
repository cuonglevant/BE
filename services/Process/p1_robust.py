"""
Robust P1 (Multiple Choice) Processing
Uses advanced preprocessing and contour-based detection
"""
import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform
from .robust_preprocessing import RobustPreprocessor


def calculate_bubble_darkness(cell):
    """
    Calculate how dark/filled a bubble cell is
    For inverted binary images: white pixels = filled
    Returns percentage of filled pixels (0-1)
    """
    if cell.size == 0:
        return 0.0
    
    # Count white pixels (filled) in inverted binary image
    filled_pixels = np.sum(cell == 255)
    total_pixels = cell.size
    
    darkness = filled_pixels / total_pixels
    return darkness


def process_p1_answers_robust(image_path=None, show_images=False, save_images=False):
    """
    Robust processing of PHẦN I - ABCD multiple choice (40 questions)
    Uses advanced preprocessing and improved bubble detection
    
    Returns:
        dict: {'answers': [(question_num, answer), ...]}
    """
    show_images = False
    
    if image_path is None:
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p12.jpg")
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Cannot read image: {image_path}")
        return {'answers': [(q, '') for q in range(1, 41)]}
    
    # Initialize robust preprocessor
    preprocessor = RobustPreprocessor()
    
    # Apply robust preprocessing
    enhanced = preprocessor.enhance_for_bubble_detection(image, aggressive=False)
    
    # Find contours using robust method
    qualified_contours = preprocessor.find_contours_robust(
        enhanced, 
        min_area=100000, 
        max_area=400000
    )
    
    # Fallback to traditional method if robust method fails
    if not qualified_contours:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)
        
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        for i, contour in enumerate(contours):
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            area = cv2.contourArea(contour)
            
            if len(approx) == 4 and 100000 < area < 400000:
                qualified_contours.append((contour, approx, area))
    
    if len(qualified_contours) < 4:
        print(f"Warning: Found only {len(qualified_contours)} answer grids, expected 4")
    
    if not qualified_contours:
        print("No P1 answer grids found")
        return {'answers': [(q, '') for q in range(1, 41)]}
    
    all_answers = {}
    
    # Process each grid (4 grids = 4x10 questions)
    for idx, (contour, approx, area, *rest) in enumerate(qualified_contours[:4]):
        try:
            paper_points = approx.reshape(4, 2)
            cropped_paper = four_point_transform(cv2.imread(image_path), paper_points)
            cropped_paper = cv2.rotate(cropped_paper, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            # Apply robust preprocessing to cropped grid
            if len(cropped_paper.shape) == 3:
                cropped_gray = cv2.cvtColor(cropped_paper, cv2.COLOR_BGR2GRAY)
            else:
                cropped_gray = cropped_paper
            
            # Enhanced preprocessing for this specific grid
            cropped_enhanced = preprocessor.adaptive_enhance(cropped_gray)
            
            # Apply thresholding with INVERT to get white bubbles on black
            _, binary = cv2.threshold(
                cropped_enhanced, 0, 255,
                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            height, width = binary.shape[:2]
            rows, cols = 11, 5
            cell_height, cell_width = height // rows, width // cols
            
            # Calculate adaptive threshold using all cells
            all_cell_means = []
            for r in range(1, rows):
                for c in range(1, cols):
                    y1, y2 = r * cell_height, (r + 1) * cell_height
                    x1, x2 = c * cell_width, (c + 1) * cell_width
                    cell = binary[y1:y2, x1:x2]
                    all_cell_means.append(np.mean(cell))
            
            # Use 65th percentile as threshold
            threshold = np.percentile(all_cell_means, 65)
            
            col_to_answer = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
            question_offset = idx * 10
            
            # Process each question row
            for row in range(1, rows):
                question_num = question_offset + row
                
                # Calculate mean brightness for each answer option
                option_means = {}
                
                for col in range(1, cols):
                    # Extract cell with small padding
                    padding = 2
                    y1 = row * cell_height + padding
                    y2 = (row + 1) * cell_height - padding
                    x1 = col * cell_width + padding
                    x2 = (col + 1) * cell_width - padding
                    
                    cell = binary[y1:y2, x1:x2]
                    
                    if cell.size == 0:
                        option_means[col] = 0
                        continue
                    
                    # Calculate mean (higher = more white = more filled)
                    mean_val = np.mean(cell)
                    option_means[col] = mean_val
                
                # Find darkest (lowest mean because we want filled bubble)
                # Wait, we inverted so white = filled, so highest mean = filled
                if option_means:
                    max_mean = max(option_means.values())
                    
                    # Check if above threshold
                    if max_mean > threshold:
                        # Find the column with max mean
                        selected_col = [
                            col for col, m in option_means.items()
                            if m == max_mean][0]
                        all_answers[question_num] = (
                            col_to_answer[selected_col])
        
        except Exception as e:
            print(f"Error processing grid {idx}: {e}")
            continue
    
    # Return sorted list
    result_answers = []
    for q in range(1, 41):
        result_answers.append((q, all_answers.get(q, '')))
    
    return {'answers': result_answers}


# Alias for compatibility
process_p1_answers = process_p1_answers_robust
