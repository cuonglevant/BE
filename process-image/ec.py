import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import four_point_transform


def process_exam_code(image_path=None, show_images=False, save_images=False):
    """
    Xử lý nhận dạng mã đề từ ảnh exam code
    
    Args:
        image_path (str): Đường dẫn đến file ảnh. Nếu None sẽ dùng "code.jpg" mặc định
        show_images (bool): Có hiển thị ảnh hay không
        save_images (bool): Có lưu ảnh kết quả hay không
    
    Returns:
        str: Mã đề được nhận dạng (4 chữ số) hoặc chuỗi rỗng nếu không tìm thấy
    """
    # Đọc và xử lý ảnh
    if image_path is None:
        image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code.jpg")
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Không thể đọc file ảnh: {image_path}")
        return ""
    
    # Tiền xử lý ảnh
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    # Tìm contours và lọc vùng mã đề
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    paper_contour = None
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        
        if len(approx) == 4 and 100000 < cv2.contourArea(contour) < 150000:
            paper_contour = approx
            break

    if paper_contour is None:
        print("Khong tim thay vung ma de!")
        return ""

    print("Da tim thay vung ma de!")
    
    try:
        # Crop và xoay ảnh
        paper_points = paper_contour.reshape(4, 2)
        cropped_paper = four_point_transform(cv2.imread(image_path), paper_points)
        cropped_paper = cv2.rotate(cropped_paper, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # Thiết lập grid
        height, width = cropped_paper.shape[:2]
        rows, cols = 10, 4
        cell_height, cell_width = height // rows, width // cols
        
        # Xử lý nhận dạng
        gray_cropped = cv2.cvtColor(cropped_paper, cv2.COLOR_BGR2GRAY)
        _, otsu_thresh = cv2.threshold(gray_cropped, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Thu thập giá trị mean và tính ngưỡng
        all_means = []
        for col in range(cols):
            for row in range(rows):
                y1, y2 = row * cell_height, (row + 1) * cell_height
                x1, x2 = col * cell_width, (col + 1) * cell_width
                cell_roi = otsu_thresh[y1:y2, x1:x2]
                all_means.append(np.mean(cell_roi))
        
        auto_threshold = np.percentile(all_means, 10)
        print(f"Nguong tu dong tinh duoc: {auto_threshold:.2f}")
        
        # Nhận dạng ô đã tô
        exam_code = []
        numbered_image = cropped_paper.copy() if show_images or save_images else None
        
        for col in range(cols):
            for row in range(rows):
                y1, y2 = row * cell_height, (row + 1) * cell_height
                x1, x2 = col * cell_width, (col + 1) * cell_width
                cell_roi = otsu_thresh[y1:y2, x1:x2]
                mean_val = np.mean(cell_roi)
                
                if numbered_image is not None:
                    cv2.putText(numbered_image, str(row), (x1 + 5, y1 + 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                    cv2.putText(numbered_image, f"{mean_val:.0f}", (x1 + 5, y2 - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)
                
                if mean_val < auto_threshold:
                    exam_code.append((col + 1, row))
                    if numbered_image is not None:
                        cv2.rectangle(numbered_image, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    print(f"Tim thay o da to tai cot {col + 1}, hang {row} (mean: {mean_val:.2f})")
        
        # Tạo kết quả
        exam_code.sort(key=lambda x: x[0])
        exam_code_string = ''.join([str(digit) for _, digit in exam_code])
        
        # Lưu và hiển thị nếu cần
        if save_images and numbered_image is not None:
            cv2.imwrite("numbered_made.jpg", numbered_image)
            print("Da luu anh co danh so vao file 'numbered_made.jpg'")
        
        if show_images and numbered_image is not None:
            cv2.imshow("Ma de co danh so", numbered_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        # Kết quả
        if len(exam_code_string) == 4:
            print(f"MA DE NHAN DANG DUOC: {exam_code_string}")
        else:
            print(f"Canh bao: Ma de khong du 4 chu so. Tim thay: {exam_code_string} ({len(exam_code_string)} chu so)")
        
        return exam_code_string
        
    except Exception as e:
        print(f"Loi khi xu ly: {e}")
        return ""


def main():
    """Hàm main để test"""
    exam_code = process_exam_code(show_images=True, save_images=True)
    print(f"\nMa de nhan dang duoc: {exam_code}")


if __name__ == "__main__":
    main()
