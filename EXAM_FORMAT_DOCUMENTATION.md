# Exam Processing System - New 3-Part Format

## Overview
The exam processing system has been completely refactored to handle the actual exam structure with three distinct sections:

## Exam Structure

### PHẦN I (Part 1) - Standard Multiple Choice
- **Format**: 40 questions with ABCD choices
- **Processing**: `process_p1_answers()` in `p1.py`
- **Output**: `[(1, 'A'), (2, 'B'), ..., (40, 'D')]`
- **Grid Structure**: 4 grids of 10 questions each

### PHẦN II (Part 2) - True/False Format  
- **Format**: 8 cells, each with "Đúng Sai" (True/False) columns
- **Sub-parts**: Each cell has parts a, b, c, d
- **Processing**: `process_p2_answers()` in `p2.py`
- **Output**: `[('p2_c1_a', 'Dung'), ('p2_c1_b', 'Sai'), ...]`
- **Grid Structure**: 2 rows × 4 columns of cells

### PHẦN III (Part 3) - Essay/Multi-row Format
- **Format**: 8 columns (Câu 1-8), each with ~10 answer rows
- **Processing**: `process_p3_answers()` in `p3.py`
- **Output**: `[('p3_c1', [1, 3, 5]), ('p3_c2', [2, 4]), ...]`
- **Grid Structure**: Single large grid with 8 columns

## Technical Details

### Image Processing Pipeline
1. **Grayscale Conversion** → Gaussian Blur → Canny Edge Detection
2. **Contour Detection** with area filtering:
   - P1: 150,000 - 300,000 pixels (standard answer grids)
   - P2: 120,000 - 145,000 pixels (True/False cells)
   - P3: 100,000 - 600,000 pixels (large essay grid)
3. **Perspective Transform** using `four_point_transform()`
4. **Threshold Calculation** using 25th percentile of mean values
5. **Answer Detection** by comparing cell mean values against threshold

### Key Functions

#### `scan_all_answers(p1_img, p2_img, p3_img)`
Main function that processes all three sections and returns:
```python
{
    'p1': [(1, 'A'), (2, 'B'), ...],        # 40 ABCD answers
    'p2': [('p2_c1_a', 'Dung'), ...],       # True/False answers
    'p3': [('p3_c1', [1, 3, 5]), ...]       # Essay marked rows
}
```

#### `score_answers(scanned_ans, correct_ans)`
Scores PHẦN I answers (40 questions) on a scale of 0-10.

## Algorithm Improvements

### 1. Grid Detection
- Uses 4-corner polygon approximation
- Filters by area range specific to each section
- Sorts by vertical position (P1) or grid position (P2)

### 2. Answer Recognition
- Dynamic threshold calculation per grid
- Rotation handling (90° counterclockwise)
- Cell-based scanning with configurable rows/columns

### 3. Format Flexibility
- P1: Single answer per question (first filled circle)
- P2: Multiple cells with sub-parts
- P3: Multiple marks per column allowed

## Testing Results
```
PHẦN I: 36/40 answered (90%)
PHẦN II: 3 sub-questions detected  
PHẦN III: 6/8 columns marked (75%)
```

## File Structure
```
services/
  Process/
    p1.py          # PHẦN I processor (ABCD)
    p2.py          # PHẦN II processor (Đúng/Sai)
    p3.py          # PHẦN III processor (Essay)
  Grade/
    create_ans.py  # Main scanning & scoring logic
```

## Usage Example
```python
from services.Grade.create_ans import scan_all_answers

results = scan_all_answers(
    'path/to/p1_image.jpg',
    'path/to/p2_image.jpg',
    'path/to/p3_image.jpg'
)

# Access results by section
p1_answers = results['p1']  # Standard ABCD
p2_answers = results['p2']  # True/False
p3_answers = results['p3']  # Essay marks
```

## Migration Notes
- **Breaking Change**: `scan_all_answers()` now returns a dictionary instead of a flat list
- **Backward Compatibility**: Legacy API endpoints need to be updated to handle new format
- **Scoring**: Currently only implements scoring for PHẦN I (ABCD questions)

## Future Enhancements
1. Implement scoring logic for PHẦN II and PHẦN III
2. Add validation for mark patterns (e.g., only one mark per sub-part)
3. Support for partial credit in essay sections
4. Enhanced error detection and reporting
5. Confidence scores for each detected answer
