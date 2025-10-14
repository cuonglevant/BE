"""
Part 3 (PHẦN III) OMR Processing
Grid-based decimal number detection

Structure:
- 8 questions arranged vertically
- Each question has 4 columns (C1, C2, C3, C4) for constructing decimal numbers
- Each column has 12 rows: -, , (comma), 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
- Students mark one bubble per column to create numbers like: -1.5, 3.14, etc.

Grid Layout:
+-------+----+----+----+----+
| Label | C1 | C2 | C3 | C4 |  <- Header
+-------+----+----+----+----+
|  -    | o  | o  | o  | o  |  <- Row 0: Negative sign
|  ,    | o  | o  | o  | o  |  <- Row 1: Comma/decimal point
|  0    | o  | o  | o  | o  |  <- Row 2
|  1    | o  | o  | o  | o  |  <- Row 3
|  2    | o  | o  | o  | o  |  <- Row 4
|  3    | o  | o  | o  | o  |  <- Row 5
|  4    | o  | o  | o  | o  |  <- Row 6
|  5    | o  | o  | o  | o  |  <- Row 7
|  6    | o  | o  | o  | o  |  <- Row 8
|  7    | o  | o  | o  | o  |  <- Row 9
|  8    | o  | o  | o  | o  |  <- Row 10
|  9    | o  | o  | o  | o  |  <- Row 11
+-------+----+----+----+----+

Based on successful P2 approach with counter-clockwise rotation.
"""

import cv2
import numpy as np
import json
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from utils import four_point_transform
except ImportError:
    # Fallback if utils not found
    def four_point_transform(image, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        (tl, tr, br, bl) = rect
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        return warped


class BalancedGridP3:
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        
        # Digit mapping for P3
        self.digit_map = ['-', ',', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    
    def detect_regions(self, image):
        """
        Detect P3 regions on the right side of the page.
        P3 has 8 separate regions (1 question each).
        
        P3 regions are SMALLER than P2 - they contain 12 rows x 4 columns of bubbles.
        Looking for aspect ratio around 2.4-2.7 (wider than tall).
        
        Uses simple thresholding with RETR_LIST to find all contours reliably.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Use simple thresholding (more reliable than Canny for P3)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        # Use RETR_LIST to get all contours (not just external)
        contours, _ = cv2.findContours(
            binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        
        valid_regions = []
        img_height, img_width = image.shape[:2]
        
        if self.debug_mode:
            print(f"\n  Analyzing image: {img_width}x{img_height}")
            print(f"  Total contours found: {len(contours)}")
        
        debug_count = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # P3 regions characteristics from actual data:
            # - Area: ~140k-155k pixels (for original 1440-width image)
            # - Aspect ratio: 2.4-2.7 (very wide/landscape)
            # - Width: ~600-650px, Height: ~240-260px
            if area < 130000 or area > 160000:
                continue
                
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            
            # Debug first 10 large contours
            if self.debug_mode and debug_count < 10:
                print(f"  Contour {debug_count}: area={area:.0f}, bbox=({x},{y},{w},{h}), aspect={aspect_ratio:.2f}")
                debug_count += 1
            
            # P3 specific filters based on working test:
            # 1. Aspect ratio: 2.4-2.7 (very wide landscape)
            # 2. Be more lenient for regions near bottom (might be cut off)
            is_bottom_region = y > (img_height * 0.85)
            
            # Width and height constraints
            min_width, max_width = 600, 700
            min_height = 200 if is_bottom_region else 230
            max_height = 280
            
            is_landscape = (aspect_ratio > 2.2 and aspect_ratio < 2.8)
            is_valid_size = (w >= min_width and w <= max_width and 
                           h >= min_height and h <= max_height)
            
            if is_landscape and is_valid_size:
                perimeter = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
                
                # Most P3 regions should be rectangular (4 corners)
                if len(approx) >= 4:
                    valid_regions.append({
                        'contour': contour,
                        'approx': approx,
                        'area': area,
                        'bbox': (x, y, w, h),
                        'aspect_ratio': aspect_ratio,
                        'position': 'right'
                    })
                    
                    if self.debug_mode:
                        print(f"  Found P3 region: area={area:.0f}, "
                              f"bbox=({x},{y},{w},{h}), "
                              f"aspect={aspect_ratio:.2f}, "
                              f"side=FAR_RIGHT")
        
        # Sort by vertical position (top to bottom)
        valid_regions.sort(key=lambda x: x['bbox'][1])
        return valid_regions
    
    def create_balanced_grid_p3(self, width, height, aspect_ratio=None):
        """
        Create grid for P3 layout - 1 QUESTION per region
        
        Each region contains ONE question with 4 columns (C1-C4)
        Each column has 12 rows: -, comma, 0-9
        
        Grid proportions based on P2 success:
        - Header: 32% (same as P2)
        - 12 evenly distributed rows for digits
        - 4 columns for the 4-digit number
        
        Args:
            width: Region width
            height: Region height
            aspect_ratio: Width/height ratio
        """
        
        # P3 has 12 data rows (-, comma, 0-9)
        # With 12 rows, we need 13 horizontal lines to create 12 spaces
        # Lines: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] = 13 lines
        # Rows: [0-1, 1-2, 2-3, 3-4, 4-5, 5-6, 6-7, 7-8, 8-9, 9-10, 10-11, 11-12] = 12 rows
        
        # However, looking at the actual image, there IS a header row with column labels (C1, C2, C3, C4)
        # So we need: 1 header space + 12 data spaces = 13 spaces = 14 lines!
        # User said "12 row so it will be 13 line" - they meant 12 DATA rows, not including header!
        # So let's create 14 lines for 13 spaces (1 header + 12 data)
        
        # Header percentage - P3 header is small (just column labels)
        header_height = int(height * 0.08)  # Only 8% for column labels
        
        # Start with just the top line
        h_lines = [0]
        
        # Add header line
        h_lines.append(header_height)
        
        remaining_height = height - header_height
        
        # 12 data rows for digits: -, comma, 0-9
        # Create 12 equal spaces in the remaining height
        # BUT: rows 4-8 need to shift up slightly for better alignment
        num_data_rows = 12
        row_height = remaining_height / num_data_rows
        
        # Add 11 more lines (rows 1-11), plus the bottom makes 12 data rows
        for i in range(1, num_data_rows):  # 1-11 = 11 iterations
            y = header_height + int(row_height * i)
            # Custom user shifts for rows 5-11:
            # i=5: row 5 (digit 4)   -> up 2% of region height
            # i=6: row 6 (digit 5)   -> up 10 px
            # i=7: row 7 (digit 6)   -> up 16 px
            # i=8: row 8 (digit 7)   -> up 22 px
            # i=9: row 9 (digit 8)   -> up 27 px
            # i=10: row 10 (digit 9) -> up 34 px
            # i=11: row 11 (digit 10)-> up 40 px
            if i == 5:
                y -= int(height * 0.02)
            elif i == 6:
                y -= 10
            elif i == 7:
                y -= 14  # Row 7 up 14px
            elif i == 8:
                y -= 20  # Row 8 up 20px
            elif i == 9:
                y -= 22  # Row 9 up 22px
            elif i == 10:
                y -= 20  # Row 10 up 20px
            elif i == 11:
                y -= 25  # Row 11 up 25px
            h_lines.append(y)
        
        # Add bottom line
        h_lines.append(height)
        
        # Total: [0, header] + 11 lines + [height] = 2 + 11 + 1 = 14 lines
        # This creates: 1 header space (0 to header) + 12 data spaces (header to height) = 13 spaces ✓
        
        # VERTICAL LINES - 4 columns for C1, C2, C3, C4
        label_width_ratio = 0.15  # Label column
        remaining_width = 1.0 - label_width_ratio
        column_width = remaining_width / 4  # 4 columns
        
        v_lines = [
            0,  # Start
            int(width * label_width_ratio),  # Label | C1
            int(width * (label_width_ratio + column_width)),  # C1 | C2
            int(width * (label_width_ratio + 2 * column_width)),  # C2 | C3
            int(width * (label_width_ratio + 3 * column_width)),  # C3 | C4
            width  # End
        ]
        
        if self.debug_mode:
            aspect_str = f"{aspect_ratio:.2f}" if aspect_ratio else "N/A"
            print(f"\nP3 Grid Configuration:")
            print(f"  Image size: {width} x {height}, aspect={aspect_str}")
            print(f"  Header height: {header_height} px (8%)")
            print(f"  Data rows: 12 (evenly spaced)")
            print(f"  H-lines: {len(h_lines)} lines")
            print(f"  V-lines: {v_lines}")
            print(f"  Layout: Label | C1 | C2 | C3 | C4")
        
        return h_lines, v_lines
    
    def save_debug_grid(self, image, h_lines, v_lines, region_name="Region"):
        """
        Save visualization showing P3 grid alignment
        """
        debug_img = image.copy()
        if len(debug_img.shape) == 2:
            debug_img = cv2.cvtColor(debug_img, cv2.COLOR_GRAY2BGR)
        
        # Draw horizontal lines
        row_labels = ["Header", "-", ",", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        for i, y in enumerate(h_lines):
            y_int = int(y)
            
            if i == 1:
                # Magenta for header end
                color = (255, 0, 255)
                thickness = 3
            else:
                color = (0, 255, 0)  # Green for rows
                thickness = 2
            
            cv2.line(debug_img, (0, y_int), (debug_img.shape[1], y_int),
                     color, thickness)
            if i < len(row_labels):
                cv2.putText(debug_img, row_labels[i], (5, y_int - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw vertical lines
        col_labels = ["Start", "Label", "C1", "C2", "C3", "C4"]
        for i, x in enumerate(v_lines):
            x_int = int(x)
            cv2.line(debug_img, (x_int, 0), (x_int, debug_img.shape[0]),
                     (255, 0, 0), 2)
            if i < len(col_labels):
                cv2.putText(debug_img, col_labels[i], (x_int + 5, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        # Add legend
        cv2.putText(debug_img, f"{region_name} - P3 Grid (Decimal Number)",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 255), 2)
        cv2.putText(debug_img, "Layout: -, comma, 0-9 rows x 4 columns",
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 0), 1)
        
        os.makedirs("debug_p3", exist_ok=True)
        filename = f"debug_p3/{region_name}_p3_grid.png"
        cv2.imwrite(filename, debug_img)
        print(f"  Saved: {filename}")
        
        # ALSO save the original region without grid for manual inspection
        original_filename = f"debug_p3/{region_name}_original.png"
        if len(image.shape) == 2:
            cv2.imwrite(original_filename, image)
        else:
            cv2.imwrite(original_filename, image)
        print(f"  Saved original: {original_filename}")
    
    def extract_cells(self, image, h_lines, v_lines):
        """
        Extract cells for P3 grid
        
        Grid structure:
        - Row 0: Header (skip)
        - Rows 1-12: -, comma, 0-9
        - Column 0: Label (skip)
        - Columns 1-4: C1, C2, C3, C4
        
        Returns: List of 48 cells (12 rows × 4 columns)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(
            image.shape) == 3 else image
        
        # Enhanced preprocessing (same as P2)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV, 15, 3
        )
        
        # Save preprocessing sample
        if self.debug_mode:
            os.makedirs("debug_p3", exist_ok=True)
            sample_path = "debug_p3/preprocessed_sample.png"
            combined = np.hstack([enhanced, denoised, binary])
            cv2.imwrite(sample_path, combined)
            print(f"  Saved preprocessing sample: {sample_path}")
        
        cells = []
        
        cells = []
        
        # With 14 lines (indices 0-13), we have 13 rows total:
        # Row 0 (header): h_lines[0] to h_lines[1] - SKIP (just column labels)
        # Row 1 ("-"): h_lines[1] to h_lines[2]
        # Row 2 (","): h_lines[2] to h_lines[3]
        # ...
        # Row 12 ("9"): h_lines[12] to h_lines[13]
        
        # Process 12 digit rows (skip header row 0)
        for data_row_idx in range(12):  # 0-11 representing the 12 digits
            # line_idx points to the TOP line of each data row
            # Data row 0 ("-") starts at h_lines[1] (after header)
            # Data row 11 ("9") starts at h_lines[12]
            line_idx = data_row_idx + 1  # Maps 0->1, 1->2, ..., 11->12
            
            # Get the digit for this row
            digit = self.digit_map[data_row_idx]  # 0-11 maps to ['-', ',', '0',...'9']
            
            # Process 4 columns (C1, C2, C3, C4)
            for col_idx in range(1, 5):
                y1 = h_lines[line_idx]
                y2 = h_lines[line_idx + 1]  # line_idx+1 ranges from 2 to 13, all valid!
                x1 = v_lines[col_idx]
                x2 = v_lines[col_idx + 1]
                
                cell_height = y2 - y1
                cell_width = x2 - x1
                
                # Minimal padding (5% - from P2 success)
                pad_y = max(2, int(cell_height * 0.05))
                pad_x = max(2, int(cell_width * 0.05))
                
                y1_pad = int(y1 + pad_y)
                y2_pad = int(y2 - pad_y)
                x1_pad = int(x1 + pad_x)
                x2_pad = int(x2 - pad_x)
                
                if y2_pad > y1_pad and x2_pad > x1_pad:
                    cell_gray = denoised[y1_pad:y2_pad, x1_pad:x2_pad]
                    cell_binary = binary[y1_pad:y2_pad, x1_pad:x2_pad]
                    
                    if cell_gray.size > 0:
                        # Use binary image for filled ratio
                        filled_pixels = np.sum(cell_binary > 0)
                        filled_ratio = filled_pixels / cell_binary.size
                        
                        # Grayscale statistics
                        mean_val = np.mean(cell_gray)
                        
                        if self.debug_mode and cell_gray.size > 0:
                            print(f"      Cell[row={digit}, "
                                  f"col=C{col_idx}] -> "
                                  f"mean={mean_val:.0f}, "
                                  f"filled={filled_ratio:.2f}")
                        
                        cell_info = {
                            'row': data_row_idx,  # 0-11 for the 12 digits
                            'col': col_idx,  # 1-4 for C1-C4
                            'digit': digit,
                            'column_name': f'C{col_idx}',
                            'filled_ratio': filled_ratio,
                            'mean': mean_val,
                            'bounds': (y1_pad, y2_pad, x1_pad, x2_pad)
                        }
                        
                        cells.append(cell_info)
        
        return cells
    
    def detect_p3_answer(self, cells):
        """
        Detect decimal number from grid cells.
        
        For each column (C1-C4), find the bubble with highest filled_ratio.
        Then construct the number from the selected digits.
        
        Returns: float number (e.g., -1.5, 3.14, 10, 1.33, etc.)
        """
        if not cells:
            return None
        
        # Group by column
        columns = {'C1': [], 'C2': [], 'C3': [], 'C4': []}
        
        for cell in cells:
            col_name = cell['column_name']
            if col_name in columns:
                columns[col_name].append(cell)
        
        # For each column, find the most filled bubble
        # IMPORTANT: Use smart thresholding to handle N/A cases
        selected_digits = []
        BUBBLE_THRESHOLD_MIN = 0.35  # Absolute minimum to be considered
        BUBBLE_THRESHOLD_GAP = 0.05  # Minimum gap between best and 2nd best for marginal cases
        
        if self.debug_mode:
            print(f"\n  === Column-by-column Detection (Top 3 per column) ===")
        
        for col_name in ['C1', 'C2', 'C3', 'C4']:
            if not columns[col_name]:
                selected_digits.append('')
                continue
            
            # Sort by filled_ratio (descending)
            sorted_cells = sorted(columns[col_name], 
                                 key=lambda x: x['filled_ratio'], 
                                 reverse=True)
            
            best_cell = sorted_cells[0]
            second_best = sorted_cells[1] if len(sorted_cells) > 1 else None
            
            # Advanced multi-factor bubble detection
            # Consider: filled_ratio, gap to 2nd best, and mean darkness
            
            gap = (best_cell['filled_ratio'] - second_best['filled_ratio']) if second_best else 0.5
            mean_val = best_cell['mean']
            filled = best_cell['filled_ratio']
            
            # Decision logic with multiple criteria:
            # 1. Strong bubbles: filled >= 0.37 OR (filled >= 0.35 AND mean < 145)
            is_strong_bubble = (filled >= 0.37) or (filled >= 0.35 and mean_val < 145)
            
            # 2. Marginal bubbles: filled >= 0.34 AND gap >= 0.05 AND mean < 165
            #    All three conditions must be met for marginal detection
            is_marginal_bubble = (filled >= 0.34 and gap >= 0.05 and mean_val < 165)
            
            # 3. Weak/noise: Everything else is N/A
            is_valid_bubble = is_strong_bubble or is_marginal_bubble
            
            if is_valid_bubble:
                selected_digit = best_cell['digit']
            else:
                # No bubble marked in this column (N/A)
                selected_digit = ''
                if self.debug_mode:
                    print(f"\n    {col_name}: N/A (filled={filled:.2f}, gap={gap:.2f}, mean={mean_val:.0f})")
            
            if self.debug_mode and is_valid_bubble:
                print(f"\n    {col_name}:")
                # Show top 3 candidates with detailed info
                for idx, cell in enumerate(sorted_cells[:3]):
                    marker = " >>> SELECTED" if idx == 0 else ""
                    print(f"      {idx+1}. '{cell['digit']:>5}': filled={cell['filled_ratio']:.2f}, "
                          f"mean={cell['mean']:.0f}{marker}")
                if self.debug_mode:
                    reason = "STRONG" if is_strong_bubble else "MARGINAL"
                    print(f"      [{reason}: filled={filled:.2f}, gap={gap:.2f}, mean={mean_val:.0f}]")
            
            selected_digits.append(selected_digit)
        
        # Construct the number
        number_str = ''.join(selected_digits)
        
        # Convert to float
        try:
            # Replace comma with decimal point
            number_str = number_str.replace(',', '.')
            # Remove any empty spaces
            number_str = number_str.strip()
            
            if number_str:
                number = float(number_str)
                return number
            else:
                return None
        except ValueError:
            if self.debug_mode:
                print(f"    Warning: Could not convert '{number_str}' to number")
            return None
    
    def process_region(self, region_image, region_idx=0, question_number=1):
        """
        Process P3 region (1 question per region)
        """
        if region_image is None or region_image.size == 0:
            return None
        
        # Check rotation based on aspect ratio
        height, width = region_image.shape[:2]
        original_aspect = width / height
        
        if self.debug_mode:
            print(f"\n  Original: {width}x{height}, aspect={original_aspect:.2f}")
        
        # Rotate counter-clockwise (same as P2 success)
        rotated = cv2.rotate(region_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        height, width = rotated.shape[:2]
        
        print(f"\nProcessing P3 Region {region_idx}:")
        
        # Create P3 grid
        h_lines, v_lines = self.create_balanced_grid_p3(width, height, original_aspect)
        
        # Save debug visualization
        self.save_debug_grid(rotated, h_lines, v_lines, f"P3_Region{region_idx}")
        
        # Extract cells
        cells = self.extract_cells(rotated, h_lines, v_lines)
        print(f"  Extracted {len(cells)} cells "
              f"(should be 48: 12 rows x 4 columns)")
        
        # Detect answer
        answer = self.detect_p3_answer(cells)
        
        if answer is not None:
            print(f"  Detected answer: {answer}")
            return {
                'question': question_number,
                'answer': answer
            }
        else:
            print(f"  Failed to detect answer")
            return None
    
    def process_part3(self, image_path):
        """
        Process Part 3 with balanced grid
        
        Expected: 8 regions, each with 1 question = 8 questions total
        """
        image = cv2.imread(image_path)
        if image is None:
            return {'answers': [], 'total_detected': 0, 'accuracy': 0.0}
        
        regions = self.detect_regions(image)
        
        all_answers = []
        
        # Process 8 regions (each has 1 question)
        for region_idx, region in enumerate(regions[:8]):
            # Handle regions with more than 4 corners by using bounding box
            approx = region['approx']
            if len(approx) != 4:
                # Use bounding box instead
                x, y, w, h = region['bbox']
                region_points = np.array([
                    [x, y],
                    [x + w, y],
                    [x + w, y + h],
                    [x, y + h]
                ], dtype="float32")
                region_image = four_point_transform(image, region_points)
            else:
                region_points = approx.reshape(4, 2)
                region_image = four_point_transform(image, region_points)
            
            # Each region = 1 question
            answer = self.process_region(
                region_image, region_idx, region_idx + 1)
            
            if answer:
                all_answers.append(answer)
        
        all_answers.sort(key=lambda x: x['question'])
        
        # Calculate accuracy
        accuracy = 0.0
        correct_count = 0
        total_questions = 0
        
        if os.path.exists("validation_clean/validation_results.json"):
            with open("validation_clean/validation_results.json", 'r') as f:
                validation = json.load(f)
            
            expected = {ans['question']: ans['answer'] for ans in validation['part3']}
            
            print(f"\n{'='*60}")
            print("P3 RESULTS:")
            print(f"{'='*60}")
            
            for answer in all_answers:
                q_num = answer['question']
                detected = answer['answer']
                exp = expected.get(q_num, None)
                
                if exp is not None:
                    # Allow small floating point tolerance
                    is_correct = abs(detected - exp) < 0.01
                    
                    if is_correct:
                        correct_count += 1
                        status = "OK"
                    else:
                        status = "WRONG"
                    
                    total_questions += 1
                    print(f"\nQ{q_num}: {detected} vs {exp} {status}")
                else:
                    print(f"\nQ{q_num}: {detected} vs [NO VALIDATION DATA]")
            
            if total_questions > 0:
                accuracy = (correct_count / total_questions) * 100
            
            print(f"\n{'='*60}")
            print("FINAL RESULTS:")
            print(f"{'='*60}")
            print(f"Total questions detected: {len(all_answers)}/8")
            print(f"Correct answers: {correct_count}/{total_questions}")
            print(f"Accuracy: {accuracy:.1f}%")
            print(f"{'='*60}")
        
        return {
            'answers': all_answers,
            'total_detected': len(all_answers),
            'accuracy': accuracy
        }


def test_balanced_p3():
    """Test function"""
    print("="*60)
    print("BALANCED GRID P3 TEST")
    print("Decimal Number Detection")
    print("="*60)
    
    omr = BalancedGridP3(debug_mode=True)
    
    # Test with p23_4.jpg - full original image with all 8 P3 regions
    image_path = "2912/p23_4.jpg"
    
    if not os.path.exists(image_path):
        print(f"Error: Test image not found: {image_path}")
        return
    
    result = omr.process_part3(image_path)
    
    return result


if __name__ == "__main__":
    test_balanced_p3()
