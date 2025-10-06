import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform


def _is_gui_available():
    """Kiem tra kha dung HighGUI (imshow/namedWindow)."""
    try:
        cv2.namedWindow("__test__", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("__test__")
        return True
    except Exception:
        return False


GUI_AVAILABLE = _is_gui_available()


def process_exam_code(image_path=None, show_images=False, save_images=False):
    global GUI_AVAILABLE
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
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code.jpg")
    
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

    # Vẽ tất cả contours để debug
    all_contours_image = image.copy()
    print(f"Tim thay {len(contours)} contours")
    
    # Chỉ vẽ các contour chữ nhật (có 4 góc)
    rectangular_contours = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        
        # Chỉ xử lý contour có 4 góc (hình chữ nhật)
        if len(approx) == 4:
            rectangular_contours.append((contour, approx, area, i))
            
            # Màu sắc dựa trên điều kiện diện tích
            if 100000 < area < 150000:
                color = (0, 255, 0)  # Xanh lá - contour phù hợp
                thickness = 3
            else:
                color = (0, 255, 255)  # Vàng - có 4 góc nhưng diện tích không phù hợp
                thickness = 2
                
            cv2.drawContours(all_contours_image, [contour], -1, color, thickness)
            
            # Vẽ thông tin contour
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(all_contours_image, f"{i}: {int(area)}", 
                           (cx-30, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    print(f"Tim thay {len(rectangular_contours)} contour hinh chu nhat trong {len(contours)} contours")
    
    # Lưu ảnh tất cả contours
    if save_images:
        cv2.imwrite("all_contours_exam_code.jpg", all_contours_image)
        print("Da luu anh tat ca contours vao file 'all_contours_exam_code.jpg'")
    
    if show_images and GUI_AVAILABLE:
        # Thu nhỏ ảnh để dễ nhìn
        height, width = all_contours_image.shape[:2]
        max_size = 800
        if max(height, width) > max_size:
            scale = max_size / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            all_contours_resized = cv2.resize(all_contours_image, (new_width, new_height))
            print(f"Thu nho anh tu {width}x{height} xuong {new_width}x{new_height}")
        else:
            all_contours_resized = all_contours_image
            
        # Hiển thị ảnh với khả năng phóng to
        try:
            cv2.namedWindow("Tat ca contours", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Tat ca contours", all_contours_resized.shape[1], all_contours_resized.shape[0])
            cv2.imshow("Tat ca contours", all_contours_resized)
            print("Nhan phim ESC de dong, phim + de phong to, phim - de thu nho")
            while True:
                key = cv2.waitKey(0) & 0xFF
                if key == 27:  # ESC
                    break
                elif key == ord('+') or key == ord('='):
                    # Phóng to
                    current_size = cv2.getWindowImageRect("Tat ca contours")
                    new_width = int(current_size[2] * 1.2)
                    new_height = int(current_size[3] * 1.2)
                    cv2.resizeWindow("Tat ca contours", new_width, new_height)
                    print(f"Phong to: {current_size[2]}x{current_size[3]} -> {new_width}x{new_height}")
                elif key == ord('-'):
                    # Thu nhỏ
                    current_size = cv2.getWindowImageRect("Tat ca contours")
                    new_width = int(current_size[2] * 0.8)
                    new_height = int(current_size[3] * 0.8)
                    cv2.resizeWindow("Tat ca contours", new_width, new_height)
                    print(f"Thu nho: {current_size[2]}x{current_size[3]} -> {new_width}x{new_height}")
            cv2.destroyAllWindows()
        except Exception:
            global GUI_AVAILABLE
            GUI_AVAILABLE = False
            cv2.imwrite("all_contours_exam_code.jpg", all_contours_image)
            print("GUI khong kha dung, da luu 'all_contours_exam_code.jpg'")
    elif show_images and not GUI_AVAILABLE:
        cv2.imwrite("all_contours_exam_code.jpg", all_contours_image)
        print("GUI khong kha dung, da luu 'all_contours_exam_code.jpg'")

    paper_contour = None
    selected_contour_idx = -1
    
    # Tìm contour phù hợp từ danh sách contour chữ nhật
    for contour, approx, area, original_idx in rectangular_contours:
        if 100000 < area < 150000:
            paper_contour = approx
            selected_contour_idx = original_idx
            break

    if paper_contour is None:
        print("Khong tim thay vung ma de phu hop trong cac contour hinh chu nhat!")
        return ""

    print(f"Da tim thay vung ma de! (Contour hinh chu nhat {selected_contour_idx})")
    
    # Vẽ contour được chọn
    selected_contour_image = image.copy()
    cv2.drawContours(selected_contour_image, [paper_contour], -1, (0, 255, 0), 3)
    
    # Vẽ 4 góc của contour được chọn
    for i, point in enumerate(paper_contour.reshape(4, 2)):
        cv2.circle(selected_contour_image, tuple(point), 8, (255, 0, 0), -1)
        cv2.putText(selected_contour_image, f"P{i+1}", 
                   (point[0]+10, point[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    
    if save_images:
        cv2.imwrite("selected_contour_exam_code.jpg", selected_contour_image)
        print("Da luu anh contour duoc chon vao file 'selected_contour_exam_code.jpg'")
    
    if show_images and GUI_AVAILABLE:
        # Thu nhỏ ảnh để dễ nhìn
        height, width = selected_contour_image.shape[:2]
        max_size = 800
        if max(height, width) > max_size:
            scale = max_size / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            selected_contour_resized = cv2.resize(selected_contour_image, (new_width, new_height))
            print(f"Thu nho anh contour tu {width}x{height} xuong {new_width}x{new_height}")
        else:
            selected_contour_resized = selected_contour_image
            
        # Hiển thị ảnh với khả năng phóng to
        try:
            cv2.namedWindow("Contour duoc chon", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Contour duoc chon", selected_contour_resized.shape[1], selected_contour_resized.shape[0])
            cv2.imshow("Contour duoc chon", selected_contour_resized)
            print("Nhan phim ESC de dong, phim + de phong to, phim - de thu nho")
            while True:
                key = cv2.waitKey(0) & 0xFF
                if key == 27:  # ESC
                    break
                elif key == ord('+') or key == ord('='):
                    # Phóng to
                    current_size = cv2.getWindowImageRect("Contour duoc chon")
                    new_width = int(current_size[2] * 1.2)
                    new_height = int(current_size[3] * 1.2)
                    cv2.resizeWindow("Contour duoc chon", new_width, new_height)
                    print(f"Phong to: {current_size[2]}x{current_size[3]} -> {new_width}x{new_height}")
                elif key == ord('-'):
                    # Thu nhỏ
                    current_size = cv2.getWindowImageRect("Contour duoc chon")
                    new_width = int(current_size[2] * 0.8)
                    new_height = int(current_size[3] * 0.8)
                    cv2.resizeWindow("Contour duoc chon", new_width, new_height)
                    print(f"Thu nho: {current_size[2]}x{current_size[3]} -> {new_width}x{new_height}")
            cv2.destroyAllWindows()
        except Exception:
            global GUI_AVAILABLE
            GUI_AVAILABLE = False
            cv2.imwrite("selected_contour_exam_code.jpg", selected_contour_image)
            print("GUI khong kha dung, da luu 'selected_contour_exam_code.jpg'")
    elif show_images and not GUI_AVAILABLE:
        cv2.imwrite("selected_contour_exam_code.jpg", selected_contour_image)
        print("GUI khong kha dung, da luu 'selected_contour_exam_code.jpg'")
    
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
        
        if show_images and numbered_image is not None and GUI_AVAILABLE:
            # Thu nhỏ ảnh để dễ nhìn
            height, width = numbered_image.shape[:2]
            max_size = 800
            if max(height, width) > max_size:
                scale = max_size / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                numbered_resized = cv2.resize(numbered_image, (new_width, new_height))
                print(f"Thu nho anh danh so tu {width}x{height} xuong {new_width}x{new_height}")
            else:
                numbered_resized = numbered_image
                
            # Hiển thị ảnh với khả năng phóng to
            try:
                cv2.namedWindow("Ma de co danh so", cv2.WINDOW_NORMAL)
                cv2.resizeWindow("Ma de co danh so", numbered_resized.shape[1], numbered_resized.shape[0])
                cv2.imshow("Ma de co danh so", numbered_resized)
                print("Nhan phim ESC de dong, phim + de phong to, phim - de thu nho")
                while True:
                    key = cv2.waitKey(0) & 0xFF
                    if key == 27:  # ESC
                        break
                    elif key == ord('+') or key == ord('='):
                        # Phóng to
                        current_size = cv2.getWindowImageRect("Ma de co danh so")
                        new_width = int(current_size[2] * 1.2)
                        new_height = int(current_size[3] * 1.2)
                        cv2.resizeWindow("Ma de co danh so", new_width, new_height)
                        print(f"Phong to: {current_size[2]}x{current_size[3]} -> {new_width}x{new_height}")
                    elif key == ord('-'):
                        # Thu nhỏ
                        current_size = cv2.getWindowImageRect("Ma de co danh so")
                        new_width = int(current_size[2] * 0.8)
                        new_height = int(current_size[3] * 0.8)
                        cv2.resizeWindow("Ma de co danh so", new_width, new_height)
                        print(f"Thu nho: {current_size[2]}x{current_size[3]} -> {new_width}x{new_height}")
                cv2.destroyAllWindows()
            except Exception:
                global GUI_AVAILABLE
                GUI_AVAILABLE = False
                cv2.imwrite("numbered_made.jpg", numbered_image)
                print("GUI khong kha dung, da luu 'numbered_made.jpg'")
        elif show_images and numbered_image is not None and not GUI_AVAILABLE:
            cv2.imwrite("numbered_made.jpg", numbered_image)
            print("GUI khong kha dung, da luu 'numbered_made.jpg'")
        
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
    exam_code = process_exam_code(show_images=GUI_AVAILABLE, save_images=True)
    print(f"\nMa de nhan dang duoc: {exam_code}")


if __name__ == "__main__":
    main()
