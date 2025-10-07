import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform
from .accuracy_improvements import AccuracyImprover


def process_p2_answers(image_path=None, show_images=False, save_images=False):
    """
    Process PHẦN II from complete answer sheet
    
    From image structure: 8 cells arranged in 2 rows x 4 columns
    Each cell has:
      - Label (Câu X)
      - Two columns: "Đúng Sai" with sub-parts a, b, c, d
    
    Args:
        image_path: Path to image file
    
    Returns:
        list: [(question_id, answer), ...]
        e.g., [('p2_c1_a', 'Dung'), ('p2_c1_b', 'Sai'), ...]
    """
    show_images = False
    
    if image_path is None:
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p23.jpg")
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Cannot read image: {image_path}")
        return []
    
    # Initialize accuracy improver
    improver = AccuracyImprover()
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)
    
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    # Find grids - P2 cells are mid-sized (around 130k-135k area)
    qualified_contours = []
    for i, contour in enumerate(contours):
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = cv2.contourArea(contour)
        
        # Target P2 cell size
        if len(approx) == 4 and 120000 < area < 145000:
            qualified_contours.append((contour, approx, area, i))
    
    if not qualified_contours:
        print("No PHẦN II cells found")
        return []
    
    # Sort by position (top to bottom, left to right)
    def sort_by_position(contours_list):
        data = []
        for contour, approx, area, idx in contours_list:
            x, y, _, _ = cv2.boundingRect(contour)
            data.append((contour, approx, area, idx, x, y))
        # Sort by row then column
        data.sort(key=lambda item: (item[5] // 100, item[4]))
        return [(c, a, ar, i) for c, a, ar, i, _, _ in data]
    
    qualified_contours = sort_by_position(qualified_contours)
    
    all_answers = []
    
    # Process each cell
    for idx, (contour, approx, area, original_idx) in enumerate(qualified_contours[:8]):  # Max 8 cells
        paper_points = approx.reshape(4, 2)
        cropped_paper = four_point_transform(cv2.imread(image_path), paper_points)
        cropped_paper = cv2.rotate(cropped_paper, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # Apply enhancement to the cropped cell for better bubble detection
        cropped_paper = improver.enhance_image_quality(cropped_paper)
        
        height, width = cropped_paper.shape[:2]
        # Structure: 5 rows (header + 4 sub-parts), 3 cols (label + Đúng + Sai)
        rows, cols = 5, 3
        cell_height, cell_width = height // rows, width // cols
        
        # Apply thresholding to the enhanced grayscale image
        _, binary = cv2.threshold(cropped_paper, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Calculate threshold - use 30th percentile for better detection
        mean_values = []
        for col in range(1, cols):
            for row in range(1, rows):
                y1, y2 = row * cell_height, (row + 1) * cell_height
                x1, x2 = col * cell_width, (col + 1) * cell_width
                cell = binary[y1:y2, x1:x2]
                mean_values.append(np.mean(cell))
        
        threshold = np.percentile(mean_values, 30)
        
        # Detect marks
        col_to_answer = {1: 'Dung', 2: 'Sai'}
        sub_parts = ['a', 'b', 'c', 'd']
        
        for row in range(1, min(rows, 5)):
            sub_part = sub_parts[row - 1]
            # Use sequential question numbering instead of cell-based
            question_num = idx * 4 + row  # 4 sub-questions per cell
            question_id = f"p2_q{question_num}_{sub_part}"
            
            answered = False
            for col in range(1, cols):
                y1, y2 = row * cell_height, (row + 1) * cell_height
                x1, x2 = col * cell_width, (col + 1) * cell_width
                cell = binary[y1:y2, x1:x2]
                mean_val = np.mean(cell)
                
                if mean_val < threshold:
                    answer = col_to_answer[col]
                    all_answers.append((question_id, answer))
                    answered = True
                    break
            
            # Add empty entry if not answered
            if not answered:
                all_answers.append((question_id, ''))
    
    return all_answers