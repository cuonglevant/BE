import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform
from .accuracy_improvements import AccuracyImprover


def process_p2_answers(image_path=None, show_images=False, save_images=False):
    """
    Process PHẦN II - Multiple True/False format
    
    Each question has 4 sub-statements (a, b, c, d)
    Each sub-statement can be marked as True (Đúng) or False (Sai)
    
    Args:
        image_path: Path to image file
    
    Returns:
        list: [(question_id, answer_dict), ...]
        e.g., [('q1', {'a': True, 'b': False, 'c': True, 'd': False}), ...]
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
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)
    
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    # Find grids - P2 cells are mid-sized (around 130k-135k area)
    # P2 has 8 cells total arranged in 2 rows x 4 columns
    qualified_contours = []
    for i, contour in enumerate(contours):
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = cv2.contourArea(contour)
        
        # Target P2 cell size - adjusted range to catch all 8 cells
        if len(approx) == 4 and 115000 < area < 150000:
            qualified_contours.append((contour, approx, area, i))
    
    if not qualified_contours:
        print("No PHẦN II cells found - this image may not contain true/false section")
        return []
    
    if len(qualified_contours) < 8:
        print(f"Warning: Found only {len(qualified_contours)} P2 cells, expected 8 - processing available cells")
    
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
        # Structure: Each cell has 4 sub-questions (a,b,c,d) with Đúng/Sai columns
        # Layout: 5 rows (1 header + 4 sub-questions), 3 cols (label + Đúng + Sai)
        rows, cols = 5, 3
        cell_height, cell_width = height // rows, width // cols
        
        # Apply thresholding to the enhanced grayscale image
        _, binary = cv2.threshold(cropped_paper, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Calculate threshold - use 30th percentile for better detection
        mean_values = []
        for row in range(1, rows):  # Skip header row
            for col in range(1, cols):  # Skip label column
                y1, y2 = row * cell_height, (row + 1) * cell_height
                x1, x2 = col * cell_width, (col + 1) * cell_width
                cell = binary[y1:y2, x1:x2]
                mean_values.append(np.mean(cell))
        
        threshold = np.percentile(mean_values, 30)
        
        # Process each sub-question (a, b, c, d)
        question_num = idx + 1
        question_id = f"q{question_num}"
        sub_answers = {}
        
        sub_question_labels = ['a', 'b', 'c', 'd']
        
        for row_idx in range(1, rows):  # Rows 1-4 for a,b,c,d
            sub_label = sub_question_labels[row_idx - 1]
            
            y1, y2 = row_idx * cell_height, (row_idx + 1) * cell_height
            
            # Check Đúng column (col 1)
            x1_dung, x2_dung = 1 * cell_width, 2 * cell_width
            dung_cell = binary[y1:y2, x1_dung:x2_dung]
            dung_mean = np.mean(dung_cell)
            
            # Check Sai column (col 2)
            x1_sai, x2_sai = 2 * cell_width, 3 * cell_width
            sai_cell = binary[y1:y2, x1_sai:x2_sai]
            sai_mean = np.mean(sai_cell)
            
            # Determine answer based on which bubble is darker (more filled)
            if dung_mean < threshold and dung_mean < sai_mean:
                sub_answers[sub_label] = True
            elif sai_mean < threshold and sai_mean < dung_mean:
                sub_answers[sub_label] = False
            else:
                # If neither or both are marked, default to None or False
                sub_answers[sub_label] = False
        
        all_answers.append((question_id, sub_answers))
    
    return all_answers