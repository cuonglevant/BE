import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform
from .accuracy_improvements import AccuracyImprover


def process_p3_answers(image_path=None, show_images=False, save_images=False):
    """
    Process PHẦN III - Numerical grid-in format
    Structure: 8 columns (Câu 1-8), each with multiple answer rows for digits
    Reconstructs numerical values from filled bubbles
    
    Args:
        image_path: Path to image file
        show_images: Display images (disabled)
        save_images: Save processed images
    
    Returns:
        list: [(question_id, numerical_value), ...]
        e.g., [('p3_c1', -1.5), ('p3_c2', 3.14), ('p3_c3', 10), ...]
    """
    show_images = False
    
    # Row to character mapping for P3 grid
    # Based on typical grid structure: -, 0-9, .
    ROW_TO_CHAR = {
        1: '-',   # Negative sign (row 1)
        2: '0',
        3: '1',
        4: '2',
        5: '3',
        6: '4',
        7: '5',
        8: '6',
        9: '7',
        10: '8',
        # Note: May need adjustment based on actual grid layout
        # Row 11 might be '9' or '.'
    }
    
    if image_path is None:
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.jpg")
    
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
        print("No PHẦN III grid found - this image may not contain essay section")
        return []
    
    # Use the largest grid if multiple found, otherwise use the first
    if len(qualified_contours) > 1:
        qualified_contours.sort(key=lambda x: x[2], reverse=True)  # Sort by area descending
    
    contour, approx, area, _ = qualified_contours[0]
    
    paper_points = approx.reshape(4, 2)
    cropped_paper = four_point_transform(cv2.imread(image_path), paper_points)
    
    # Apply enhancement to the cropped grid for better mark detection
    cropped_paper = improver.enhance_image_quality(cropped_paper)
    
    height, width = cropped_paper.shape[:2]
    # Grid: 8 columns (Câu 1-8 as shown in exam images), ~10 rows per column
    rows, cols = 11, 9  # 11 rows (1 header + 10 answer rows), 9 cols (1 label + 8 questions)
    cell_height, cell_width = height // rows, width // cols
    
    # Apply thresholding to the enhanced grayscale image
    _, binary = cv2.threshold(cropped_paper, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Calculate threshold - use 30th percentile
    mean_values = []
    for col in range(1, cols):
        for row in range(1, rows):
            y1, y2 = row * cell_height, (row + 1) * cell_height
            x1, x2 = col * cell_width, (col + 1) * cell_width
            cell = binary[y1:y2, x1:x2]
            mean_values.append(np.mean(cell))
    
    threshold = np.percentile(mean_values, 30)
    
    # Helper function to reconstruct number from marked rows
    def reconstruct_number_from_bubbles(marked_rows, row_char_map):
        """
        Reconstruct numerical value from filled bubbles.
        
        Args:
            marked_rows: List of marked row numbers
            row_char_map: Dictionary mapping row numbers to characters
        
        Returns:
            float or None: Reconstructed number
        """
        if not marked_rows:
            return None
        
        # Build string from marked bubbles
        number_string = ""
        for row_num in marked_rows:
            if row_num in row_char_map:
                number_string += row_char_map[row_num]
        
        if not number_string:
            return None
        
        # Try to convert to number
        try:
            # Handle special cases
            if number_string == '-':
                return None  # Just negative sign without number
            
            # Convert to float
            return float(number_string)
        except ValueError:
            # If conversion fails, return None
            print(f"Warning: Could not convert '{number_string}' to number")
            return None
    
    # Detect marks and reconstruct numbers
    all_answers = []
    
    for col in range(1, cols):  # Columns 1-8 for Câu 1-8
        question_id = f"p3_c{col}"
        marked_rows = []  # Store marked row numbers
        
        for row in range(1, rows):
            y1, y2 = row * cell_height, (row + 1) * cell_height
            x1, x2 = col * cell_width, (col + 1) * cell_width
            cell = binary[y1:y2, x1:x2]
            mean_val = np.mean(cell)
            
            if mean_val < threshold:
                # Store the actual row number (1-based)
                marked_rows.append(row)
        
        # Reconstruct the numerical value from marked rows
        reconstructed_value = reconstruct_number_from_bubbles(marked_rows, ROW_TO_CHAR)
        all_answers.append((question_id, reconstructed_value))
    
    return all_answers
