import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform


def process_p3_answers(image_path=None, show_images=False, save_images=False):
    """
    Process PHẦN III - Essay/Multi-row format
    Structure: 8 columns (Câu 1-8), each with multiple answer rows
    Each cell can be marked independently
    
    Args:
        image_path: Path to image file
        show_images: Display images (disabled)
        save_images: Save processed images
    
    Returns:
        list: [(question_id, row_marks), ...]
        e.g., [('p3_c1', [1, 3, 5]), ('p3_c2', [2, 4]), ...]
        where numbers indicate marked rows
    """
    show_images = False
    
    if image_path is None:
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.jpg")
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Cannot read image: {image_path}")
        return []
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)
    
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    # Find large grid for essay section
    qualified_contours = []
    for i, contour in enumerate(contours):
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = cv2.contourArea(contour)
        
        # Adjusted for actual image - try wider range
        if len(approx) == 4 and 100000 < area < 600000:
            qualified_contours.append((contour, approx, area, i))
    
    if not qualified_contours:
        print("No PHẦN III grid found")
        return []
    
    # Use the largest grid
    qualified_contours.sort(key=lambda x: x[2], reverse=True)
    contour, approx, area, _ = qualified_contours[0]
    
    paper_points = approx.reshape(4, 2)
    cropped_paper = four_point_transform(cv2.imread(image_path), paper_points)
    
    height, width = cropped_paper.shape[:2]
    # Grid: 8 columns (Câu 1-8), ~10 rows per column
    rows, cols = 11, 9  # 11 rows (1 header + 10 answer rows), 9 cols (1 label + 8 questions)
    cell_height, cell_width = height // rows, width // cols
    
    gray_cropped = cv2.cvtColor(cropped_paper, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray_cropped, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Calculate threshold - use 30th percentile
    mean_values = []
    for col in range(1, cols):
        for row in range(1, rows):
            y1, y2 = row * cell_height, (row + 1) * cell_height
            x1, x2 = col * cell_width, (col + 1) * cell_width
            cell = binary[y1:y2, x1:x2]
            mean_values.append(np.mean(cell))
    
    threshold = np.percentile(mean_values, 30)
    
    # Detect marks and attempt to read symbols
    all_answers = []
    
    # Row labels (symbols that might appear)
    row_labels = ['-', ',', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    
    for col in range(1, cols):  # Columns 1-8 for Câu 1-8
        question_id = f"p3_c{col}"
        marked_items = []  # Store (row_num, symbol) tuples
        
        for row in range(1, rows):
            y1, y2 = row * cell_height, (row + 1) * cell_height
            x1, x2 = col * cell_width, (col + 1) * cell_width
            cell = binary[y1:y2, x1:x2]
            mean_val = np.mean(cell)
            
            if mean_val < threshold:
                # Try to determine the symbol based on row position
                # Row 1-10 typically map to symbols 0-9 or special chars
                if row <= len(row_labels):
                    symbol = row_labels[row - 1]
                else:
                    symbol = str(row)
                marked_items.append(symbol)
        
        if marked_items:
            all_answers.append((question_id, marked_items))
        else:
            all_answers.append((question_id, []))
    
    return all_answers
