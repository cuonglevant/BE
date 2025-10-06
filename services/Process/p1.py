import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform


def process_p1_answers(image_path=None, show_images=False, save_images=False):
    """
    Xử lý nhận dạng đáp án từ ảnh p1
    
    Args:
        image_path (str): Đường dẫn đến file ảnh. Nếu None sẽ dùng "p1.jpg" mặc định
        show_images (bool): Có hiển thị ảnh hay không
        save_images (bool): Có lưu ảnh kết quả hay không
    
    Returns:
        list: Danh sách 40 đáp án theo thứ tự từ câu 1-40 [(câu, đáp án), ...]
              Ví dụ: [(1, 'A'), (2, 'B'), (3, ''), (4, 'C'), ...]
              Contour 1: câu 1-10, Contour 2: câu 11-20, Contour 3: câu 21-30, Contour 4: câu 31-40
    """
    # Luon tat hien thi GUI
    show_images = False

    # Đọc và xử lý ảnh
    if image_path is None:
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p12.jpg")
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Không thể đọc file ảnh: {image_path}")
        return []
    
    # Tiền xử lý ảnh
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    # Tìm contours và lọc
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    print(f"Tim thay {len(contours)} contours")

    # Vẽ tất cả contours để debug
    all_contours_image = image.copy()
    
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
            if 200000 < area < 250000:
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
        cv2.imwrite("all_contours_p1.jpg", all_contours_image)
        print("Da luu anh tat ca contours vao file 'all_contours_p1.jpg'")
    
    # Bo hoan toan hien thi GUI

    # Tìm contours đạt yêu cầu (4 góc, diện tích phù hợp)
    qualified_contours = []
    for contour, approx, area, original_idx in rectangular_contours:
        if 200000 < area < 250000:
            qualified_contours.append((contour, approx, area, original_idx))
            print(f"Contour {original_idx}: 4 goc, dien tich = {area:.0f} pixels - DAT YEU CAU")

    print(f"Tong cong tim thay {len(qualified_contours)} contour dat yeu cau")

    if not qualified_contours:
        print("Khong tim thay contour nao dat yeu cau!")
        return []

    # Sắp xếp theo vị trí từ trên xuống dưới
    qualified_contours.sort(key=lambda x: cv2.boundingRect(x[0])[1])
    
    detected_answers = []
    
    # Xử lý từng contour
    for idx, (contour, approx, area, original_idx) in enumerate(qualified_contours):
        print(f"\n=== XU LY CONTOUR {idx + 1}/{len(qualified_contours)} ===")
        print(f"Contour {original_idx}: dien tich = {area:.0f} pixels")
        
        try:
            # Vẽ contour được chọn
            selected_contour_image = image.copy()
            cv2.drawContours(selected_contour_image, [contour], -1, (0, 255, 0), 3)
            
            # Vẽ 4 góc của contour được chọn
            for i, point in enumerate(approx.reshape(4, 2)):
                cv2.circle(selected_contour_image, tuple(point), 8, (255, 0, 0), -1)
                cv2.putText(selected_contour_image, f"P{i+1}", 
                           (point[0]+10, point[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            if save_images:
                cv2.imwrite(f"selected_contour_p1_{idx + 1}_{original_idx}.jpg", selected_contour_image)
                print(f"  Da luu anh contour duoc chon vao file 'selected_contour_p1_{idx + 1}_{original_idx}.jpg'")
            
            if False:
                # Thu nhỏ ảnh để dễ nhìn
                height, width = selected_contour_image.shape[:2]
                max_size = 800
                if max(height, width) > max_size:
                    scale = max_size / max(height, width)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    selected_contour_resized = cv2.resize(selected_contour_image, (new_width, new_height))
                    print(f"  Thu nho anh contour tu {width}x{height} xuong {new_width}x{new_height}")
                else:
                    selected_contour_resized = selected_contour_image
                    
                # Hiển thị ảnh với khả năng phóng to
                pass

            # Crop và xoay ảnh
            paper_points = approx.reshape(4, 2)
            cropped_paper = four_point_transform(cv2.imread(image_path), paper_points)
            cropped_paper = cv2.rotate(cropped_paper, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            # Thiết lập grid
            height, width = cropped_paper.shape[:2]
            rows, cols = 11, 5
            cell_height, cell_width = height // rows, width // cols
            
            # Xử lý nhận dạng
            gray_cropped = cv2.cvtColor(cropped_paper, cv2.COLOR_BGR2GRAY)
            _, binary_otsu = cv2.threshold(gray_cropped, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Thu thập giá trị mean và tính ngưỡng
            all_mean_values = []
            for col in range(1, cols):
                for row in range(1, rows):
                    y1, y2 = row * cell_height, (row + 1) * cell_height
                    x1, x2 = col * cell_width, (col + 1) * cell_width
                    cell_binary = binary_otsu[y1:y2, x1:x2]
                    all_mean_values.append(np.mean(cell_binary))
            
            threshold = np.percentile(all_mean_values, 25)
            print(f"  Nguong tu dong: {threshold:.1f}")
            
            # Nhận dạng ô đã tô
            ans = []
            numbered_image = cropped_paper.copy() if show_images or save_images else None
            
            # Mapping cột thành đáp án: cột 1=A, cột 2=B, cột 3=C, cột 4=D
            col_to_answer = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
            
            # Tính toán offset câu hỏi dựa trên thứ tự contour
            # Contour 0: câu 1-10, Contour 1: câu 11-20, Contour 2: câu 21-30, Contour 3: câu 31-40
            question_offset = idx * 10
            
            for col in range(1, cols):
                for row in range(1, rows):
                    y1, y2 = row * cell_height, (row + 1) * cell_height
                    x1, x2 = col * cell_width, (col + 1) * cell_width
                    
                    cell_binary = binary_otsu[y1:y2, x1:x2]
                    mean_val = np.mean(cell_binary)
                    
                    if numbered_image is not None:
                        cv2.putText(numbered_image, str(row), 
                                   (x1 + 2, y1 + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)
                        cv2.putText(numbered_image, f"{mean_val:.0f}", 
                                   (x1 + 2, y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 255, 255), 1)
                    
                    if mean_val < threshold:
                        question_num = question_offset + row  # Tính số câu thực tế
                        answer_letter = col_to_answer[col]  # cột 1 = A, cột 2 = B, ...
                        ans.append((question_num, answer_letter))
                        if numbered_image is not None:
                            cv2.rectangle(numbered_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        print(f"    ✓ O da to tai cau {question_num}, dap an {answer_letter} - Mean: {mean_val:.1f}")
            
            # Tạo kết quả - sắp xếp theo số câu
            ans.sort(key=lambda x: x[0])
            contour_string = ', '.join([f"({q},{a})" for q, a in ans])
            
            # Lưu và hiển thị nếu cần
            if save_images and numbered_image is not None:
                cv2.imwrite(f"numbered_{idx + 1}_{original_idx}.jpg", numbered_image)
                print(f"Da luu anh co danh so vao file 'numbered_{idx + 1}_{original_idx}.jpg'")
            
            if False and numbered_image is not None:
                pass
            
            # Kết quả
            if len(ans) > 0:
                print(f"Dap An CONTOUR {idx + 1}: {contour_string} ✓")
            else:
                print(f"Khong nhan dang duoc dap an nao cho CONTOUR {idx + 1} ⚠️")
            
            detected_answers.append(ans)  # Trả về list các tuple (câu, đáp án)
            
        except Exception as e:
            print(f"Loi khi xu ly contour {idx + 1}: {e}")
            continue
    
    # Ghép tất cả đáp án từ các contours thành một danh sách duy nhất
    all_answers = []
    for contour_answers in detected_answers:
        all_answers.extend(contour_answers)
    
    # Loại bỏ trùng lặp và tạo dictionary để tra cứu nhanh
    answers_dict = {}
    for q, a in all_answers:
        if q not in answers_dict:  # Giữ đáp án đầu tiên nếu có trùng lặp
            answers_dict[q] = a
    
    # Tạo danh sách đầy đủ từ câu 1 đến 40
    complete_answers = []
    for i in range(1, 41):
        if i in answers_dict:
            complete_answers.append((i, answers_dict[i]))
        else:
            complete_answers.append((i, ''))  # Câu không tô để trống
    
    print("\n=== KET QUA TONG HOP ===")
    detected_count = len([a for _, a in complete_answers if a != ''])
    print(f"Tong cong nhan dang duoc {detected_count}/40 dap an")
    
    # Hiển thị các đáp án đã nhận dạng
    detected_answers_str = ', '.join([f"({q},{a})" for q, a in complete_answers if a != ''])
    if detected_answers_str:
        print(f"Cac dap an da nhan dang: {detected_answers_str}")
    
    # Hiển thị các câu còn thiếu
    missing_questions = [q for q, a in complete_answers if a == '']
    if missing_questions:
        print(f"⚠️ Thieu cac cau: {missing_questions}")
    else:
        print("✓ Da nhan dang du 40 cau!")
    
    return complete_answers


def main():
    """Hàm main để test"""
    answers = process_p1_answers(show_images=False, save_images=True)
    print(f"\nKet qua cuoi cung: {answers}")


if __name__ == "__main__":
    main()
