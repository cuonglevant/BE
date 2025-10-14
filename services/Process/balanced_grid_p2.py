"""
BALANCED GRID P2 - True/False Multiple Choice
Applies proven P1 methodology to P2 structure

P2 Format:
- 8 Questions (Câu 1-8) arranged in 4 pairs
- Each option has 4 options (a, b, c, d)
- Each option has 2 bubbles: "Dung" (True) and "Sai" (False)
- Grid: 4 rows × (2 questions × 2 bubbles) = 4 rows × 4 columns per region

Based on P1 100% success with:
- Counter-clockwise rotation
- Balanced grid with H5+ correction
- Multi-criteria bubble detection
- Visual debugging
"""
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import json
import sys
import os

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

from utils import four_point_transform


class BalancedGridP2:
    """
    P2 OMR with balanced grid alignment - True/False multiple choice
    """
    
    def __init__(self):
        self.debug_mode = True
        os.makedirs("debug_p2", exist_ok=True)
        
    def detect_regions(self, image):
        """
        Detect P2 regions - looking for smaller rectangular regions
        with specific aspect ratio (more square-like than P1)
        
        P2 regions are typically:
        - Smaller than P1 regions (4 rows vs 10 rows)
        - More square-like aspect ratio (width ~= height)
        - Located on left side of page
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL,
                                      cv2.CHAIN_APPROX_SIMPLE)
        
        valid_regions = []
        img_height, img_width = image.shape[:2]
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # P2 regions are smaller - adjust thresholds
            if area < 10000 or area > 200000:
                continue
                
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                
                # P2 specific filters:
                # 1. Aspect ratio: width should be 0.6 to 1.5 times height
                #    (more square than P1 which is tall/narrow)
                aspect_ratio = w / h if h > 0 else 0
                
                # 2. Should be on left half of image (P2 is left, P1 is right)
                is_left_side = (x + w/2) < (img_width * 0.6)
                
                # 3. Reasonable size range - ONLY small regions (0.7-1.0 aspect)
                # Filter out large regions (1.3+) which are wrong detections
                size_ok = 0.7 < aspect_ratio < 1.0
                
                if size_ok and is_left_side:
                    valid_regions.append({
                        'contour': contour,
                        'approx': approx,
                        'area': area,
                        'bbox': (x, y, w, h),
                        'aspect_ratio': aspect_ratio,
                        'position': 'left' if is_left_side else 'right'
                    })
                    
                    if self.debug_mode:
                        print(f"  Found region: area={area}, "
                              f"bbox=({x},{y},{w},{h}), "
                              f"aspect={aspect_ratio:.2f}, "
                              f"side={'LEFT' if is_left_side else 'right'}")
        
        # Sort by vertical position (top to bottom) for P2
        valid_regions.sort(key=lambda x: x['bbox'][1])
        return valid_regions
    
    def create_balanced_grid_p2(self, width, height, aspect_ratio=None):
        """
        Create grid for P2 layout - TWO QUESTIONS per region
        
        Each region contains TWO questions with 4 options each (a,b,c,d)
        Each option has 2 bubbles: Đúng and Sai
        
        Structure per region (2 questions):
        - Header row: 32% (tight to properly align row 'a')
        - Row a: ends at 44%
        - Row b: (implicit, between a and c)
        - Row c: ends at 72%
        - Row d: ends at 100%
        
        Args:
            width: Region width
            height: Region height
            aspect_ratio: Width/height ratio (not used anymore)
        """
        
        # FIXED configuration based on user specification
        # Header is 32% to properly align with row 'a'
        header_height = int(height * 0.32)
        
        h_lines = [0, header_height]
        
        remaining_height = height - header_height
        
        # User-specified row positions: header=32%, a=35%, b=50%, c=70%, d=100%
        row_positions = [
            0.35,   # Row a ends at 35% of remaining
            0.50,   # Row b ends at 50% of remaining
            0.70,   # Row c ends at 70% of remaining
            1.00    # Row d ends at 100% (bottom)
        ]
        
        for pos in row_positions:
            y = header_height + int(remaining_height * pos)
            h_lines.append(y)
        
        # VERTICAL LINES - 2 questions side by side
        # Layout: Label | Q1-Đúng | Q1-Sai | Q2-Đúng | Q2-Sai
        label_width_ratio = 0.15  # Label column (a/b/c/d)
        remaining_width = 1.0 - label_width_ratio
        question_width = remaining_width / 2  # 2 questions
        bubble_width = question_width / 2  # 2 bubbles per question
        
        v_lines = [
            0,  # Start
            int(width * label_width_ratio),  # Label | Q1-Đúng
            int(width * (label_width_ratio + bubble_width)),  # Q1-Đúng | Q1-Sai
            int(width * (label_width_ratio + question_width)),  # Q1-Sai | Q2-Đúng
            int(width * (label_width_ratio + question_width + bubble_width)),  # Q2-Đúng | Q2-Sai
            width  # End
        ]
        
        if self.debug_mode:
            aspect_str = f"{aspect_ratio:.2f}" if aspect_ratio else "N/A"
            print(f"\nP2 Grid Configuration (FIXED SPACING):")
            print(f"  Image size: {width} x {height}, aspect={aspect_str}")
            print(f"  Header height: {header_height} px (32%)")
            print(f"  Row positions: {row_positions}")
            print(f"  H-lines: {[int(h) for h in h_lines]}")
            print(f"  V-lines: {v_lines}")
            print("  Layout: Label | Dung | Sai")
        
        return h_lines, v_lines
    
    def save_debug_grid(self, image, h_lines, v_lines,
                        region_name="Region"):
        """
        Save visualization showing P2 grid alignment
        """
        debug_img = image.copy()
        if len(debug_img.shape) == 2:
            debug_img = cv2.cvtColor(debug_img, cv2.COLOR_GRAY2BGR)
        
        # Draw horizontal lines
        row_labels = ["Start", "Header", "Row-a", "Row-b", "Row-c", "Row-d"]
        for i, y in enumerate(h_lines):
            y_int = int(y)
            
            if i == 0:
                color = (128, 128, 128)  # Gray for start
                thickness = 1
            elif i == 1:
                color = (255, 0, 255)  # Magenta for header end
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
        col_labels = ["Start", "Label", "Dung", "Sai"]
        for i, x in enumerate(v_lines):
            x_int = int(x)
            cv2.line(debug_img, (x_int, 0), (x_int, debug_img.shape[0]),
                     (255, 0, 0), 2)
            if i < len(col_labels):
                cv2.putText(debug_img, col_labels[i], (x_int + 5, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        # Add legend
        cv2.putText(debug_img, f"{region_name} - P2 Grid (Dung/Sai)",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 255), 2)
        cv2.putText(debug_img, "Layout: a/b/c/d rows, Single Question",
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 0), 1)
        
        filename = f"debug_p2/{region_name}_p2_grid.png"
        cv2.imwrite(filename, debug_img)
        print(f"  Saved: {filename}")
    
    def extract_cells(self, image, h_lines, v_lines):
        """
        Extract cells for P2 grid - TWO QUESTIONS VERSION
        
        Grid structure:
        - Row 0: Header (skip)
        - Rows 1-4: Options a, b, c, d
        - Column 0: Label (skip)
        - Columns 1-4: Q1-Đúng, Q1-Sai, Q2-Đúng, Q2-Sai
        
        Returns: List of 16 cells (4 rows × 4 bubble columns)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(
            image.shape) == 3 else image
        
        # Enhanced preprocessing with stronger contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # Apply adaptive thresholding for better bubble detection
        # Try different parameters for P2
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV, 15, 3
        )
        
        # Save a sample for debugging
        if self.debug_mode:
            sample_path = f"debug_p2/preprocessed_sample.png"
            combined = np.hstack([enhanced, denoised, binary])
            cv2.imwrite(sample_path, combined)
            print(f"  Saved preprocessing sample: {sample_path}")
        
        cells = []
        
        # Process ALL 4 rows: a, b, c, d (rows 1-4 after header)
        for row_idx in range(1, 5):
            # Map row to option
            option = chr(ord('a') + (row_idx - 1))  # 1→a, 2→b, 3→c, 4→d
            
            # Process 4 bubble columns for 2 questions
            # Columns: 1=Q1-Đúng, 2=Q1-Sai, 3=Q2-Đúng, 4=Q2-Sai
            for col_idx in range(1, 5):
                y1 = h_lines[row_idx]
                y2 = h_lines[row_idx + 1]
                x1 = v_lines[col_idx]
                x2 = v_lines[col_idx + 1]
                
                cell_height = y2 - y1
                cell_width = x2 - x1
                
                # Determine question number and bubble type
                if col_idx in [1, 2]:
                    question_num = 1
                    is_true = (col_idx == 1)  # col 1 = Đúng, col 2 = Sai
                else:
                    question_num = 2
                    is_true = (col_idx == 3)  # col 3 = Đúng, col 4 = Sai
                
                # Minimal padding (5% - from P1 success)
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
                        # Use binary image for filled ratio (most reliable)
                        filled_pixels = np.sum(cell_binary > 0)
                        filled_ratio = filled_pixels / cell_binary.size
                        
                        # Grayscale statistics (backup metrics)
                        mean_val = np.mean(cell_gray)
                        median_val = np.median(cell_gray)
                        min_val = np.min(cell_gray)
                        std_val = np.std(cell_gray)
                        
                        p10 = np.percentile(cell_gray, 10)
                        p25 = np.percentile(cell_gray, 25)
                        p50 = np.percentile(cell_gray, 50)
                        
                        # Darkness metrics
                        very_dark = np.sum(cell_gray < 80)
                        dark = np.sum(cell_gray < 120)
                        darkness_ratio = dark / cell_gray.size
                        very_dark_ratio = very_dark / cell_gray.size
                        
                        # Display info for debugging
                        if self.debug_mode and cell_gray.size > 0:
                            bubble_type = 'Dung' if is_true else 'Sai'
                            print(f"      Cell[row={option}, "
                                  f"col={col_idx}] -> "
                                  f"Q{question_num}-{option}-{bubble_type}, "
                                  f"mean={mean_val:.0f}, "
                                  f"filled={filled_ratio:.2f}")
                        
                        cell_info = {
                            'row': row_idx - 1,  # 0-3 for a-d
                            'col': col_idx - 1,  # 0-3 for the 4 bubbles
                            'question': question_num,
                            'option': option,  # a, b, c, d
                            'is_true': is_true,
                            'filled_ratio': filled_ratio,
                            'mean': mean_val,
                            'median': median_val,
                            'min': min_val,
                            'std': std_val,
                            'p10': p10,
                            'p25': p25,
                            'p50': p50,
                            'darkness_ratio': darkness_ratio,
                            'very_dark_ratio': very_dark_ratio,
                            'cell_size': cell_gray.size
                        }
                        
                        cells.append(cell_info)
        
        return cells
    
    def detect_p2_answers(self, cells):
        """
        Detect P2 answers - SIMPLE DIRECT COMPARISON
        
        For each option (a/b/c/d) in each question:
        - Compare mean of "Đúng" bubble vs "Sai" bubble
        - Lower mean = darker = filled
        - If Đúng is darker → answer is TRUE
        - If Sai is darker → answer is FALSE
        """
        if not cells:
            return []
        
        # Group by question and option
        question_options = {}
        
        for cell in cells:
            q_num = cell['question']
            option = cell['option']
            is_true = cell['is_true']
            
            # Store cell data
            if q_num not in question_options:
                question_options[q_num] = {}
            if option not in question_options[q_num]:
                question_options[q_num][option] = {
                    'true_cell': None,
                    'false_cell': None
                }
            
            if is_true:
                question_options[q_num][option]['true_cell'] = cell
            else:
                question_options[q_num][option]['false_cell'] = cell
        
        # Determine answers by direct comparison
        detected_answers = []
        
        for q_num in sorted(question_options.keys()):
            answers = {'a': False, 'b': False, 'c': False, 'd': False}
            
            for option in ['a', 'b', 'c', 'd']:
                if option in question_options[q_num]:
                    true_cell = question_options[q_num][option]['true_cell']
                    false_cell = question_options[q_num][option]['false_cell']
                    
                    if true_cell and false_cell:
                        # Primary: use filled_ratio from binary thresholding
                        true_filled = true_cell['filled_ratio']
                        false_filled = false_cell['filled_ratio']
                        
                        # Secondary: use mean for backup
                        true_mean = true_cell['mean']
                        false_mean = false_cell['mean']
                        
                        # Compare filled ratios (higher = more filled)
                        filled_diff = abs(true_filled - false_filled)
                        
                        if filled_diff >= 0.05:  # 5% difference threshold
                            if true_filled > false_filled:
                                # Dung bubble is more filled -> TRUE
                                answers[option] = True
                                if self.debug_mode:
                                    print(f"    Q{q_num}-{option}: TRUE "
                                          f"(Dung filled={true_filled:.2f} > "
                                          f"Sai={false_filled:.2f})")
                            else:
                                # Sai bubble is more filled -> FALSE
                                answers[option] = False
                                if self.debug_mode:
                                    print(f"    Q{q_num}-{option}: FALSE "
                                          f"(Sai filled={false_filled:.2f} > "
                                          f"Dung={true_filled:.2f})")
                        else:
                            # Too close - use mean as tiebreaker
                            # Lower mean = darker = filled
                            if true_mean < false_mean:
                                answers[option] = True
                            else:
                                answers[option] = False
                            
                            if self.debug_mode:
                                print(f"    Q{q_num}-{option}: "
                                      f"{answers[option]} (tiebreak: "
                                      f"mean Dung={true_mean:.0f}, "
                                      f"Sai={false_mean:.0f})")
            
            detected_answers.append({
                'question': q_num,
                'answers': answers
            })
        
        return detected_answers
    
    def process_region(self, region_image, region_idx=0, question_offset=0):
        """
        Process P2 region (2 questions per region)
        """
        if region_image is None or region_image.size == 0:
            return []
        
        # Check rotation based on aspect ratio
        height, width = region_image.shape[:2]
        original_aspect = width / height  # BEFORE rotation
        
        if self.debug_mode:
            print(f"\n  Original: {width}x{height}, aspect={original_aspect:.2f}")
        
        # Rotate counter-clockwise (from P1 success)
        rotated = cv2.rotate(region_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        height, width = rotated.shape[:2]
        
        print(f"\nProcessing P2 Region {region_idx}:")
        
        # Create P2 grid with adaptive spacing based on ORIGINAL aspect ratio
        # Small original aspect (~0.83) needs EVEN spacing (these were correct!)
        # Large original aspect (~1.35) needs TIGHT spacing (these need fixing!)
        h_lines, v_lines = self.create_balanced_grid_p2(width, height, original_aspect)
        
        # Save debug visualization
        self.save_debug_grid(rotated, h_lines, v_lines, f"P2_Region{region_idx}")
        
        # Extract cells
        cells = self.extract_cells(rotated, h_lines, v_lines)
        print(f"  Extracted {len(cells)} cells "
              f"(should be 16: 4 rows x 4 columns for 2 questions)")
        
        # Detect answers
        detected = self.detect_p2_answers(cells)
        print(f"  Detected {len(detected)} questions")
        
        # Adjust question numbers based on region
        # Each region has 2 questions: Q1 and Q2
        # Region 0 → Q1, Q2; Region 1 → Q3, Q4; etc.
        for ans in detected:
            ans['question'] = question_offset + ans['question']
        
        return detected
    
    def process_part2(self, image_path):
        """
        Process Part 2 with balanced grid
        
        Expected: 4 regions, each with 2 questions = 8 questions total
        """
        image = cv2.imread(image_path)
        if image is None:
            return {'answers': [], 'total_detected': 0, 'accuracy': 0.0}
        
        regions = self.detect_regions(image)
        
        all_answers = []
        
        # Process 4 regions (each has 2 questions) = 8 questions total
        question_offset = 0
        for region_idx, region in enumerate(regions[:4]):
            region_points = region['approx'].reshape(4, 2)
            region_image = four_point_transform(image, region_points)
            
            # Each region contains 2 questions
            region_answers = self.process_region(
                region_image, region_idx, question_offset)
            all_answers.extend(region_answers)
            question_offset += 2  # Increment by 2 since each region has 2 questions
        
        all_answers.sort(key=lambda x: x['question'])
        
        # Calculate accuracy
        accuracy = 0.0
        correct_count = 0
        total_options = 0
        
        if os.path.exists("validation_clean/validation_results.json"):
            with open("validation_clean/validation_results.json", 'r') as f:
                validation = json.load(f)
            
            expected = {ans['question']: ans['answers'] for ans in validation['part2']}
            
            print(f"\n{'='*60}")
            print("P2 RESULTS:")
            print(f"{'='*60}")
            
            for answer in all_answers:
                q_num = answer['question']
                detected = answer['answers']
                exp = expected.get(q_num, {})
                
                print(f"\nQ{q_num}:")
                for option in ['a', 'b', 'c', 'd']:
                    det_val = detected.get(option, False)
                    exp_val = exp.get(option, False)
                    is_correct = det_val == exp_val
                    
                    if is_correct:
                        correct_count += 1
                        status = "OK"
                    else:
                        status = "X"
                    
                    total_options += 1
                    print(f"  {option}: {det_val} vs {exp_val} {status}")
            
            if total_options > 0:
                accuracy = (correct_count / total_options) * 100
        
        return {
            'answers': all_answers,
            'total_detected': len(all_answers),
            'correct_count': correct_count,
            'total_options': total_options,
            'accuracy': accuracy
        }


def test_balanced_p2():
    """
    Test the balanced grid P2 processor
    """
    print("="*60)
    print("BALANCED GRID P2 TEST")
    print("True/False Multiple Choice (Dung/Sai)")
    print("="*60)
    
    omr = BalancedGridP2()
    
    # Test with p12_1.jpg as per user's request
    image_path = "2912/p12_1.jpg"
    result = omr.process_part2(image_path)
    
    print(f"\n{'='*60}")
    print("FINAL RESULTS:")
    print(f"{'='*60}")
    print(f"Total questions detected: {result['total_detected']}/8")
    print(f"Total options: {result['total_options']}/32")
    print(f"Correct options: {result['correct_count']}/{result['total_options']}")
    print(f"Accuracy: {result['accuracy']:.1f}%")
    print(f"{'='*60}")
    
    return result


if __name__ == "__main__":
    test_balanced_p2()
