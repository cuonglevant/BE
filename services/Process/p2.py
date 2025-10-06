import cv2
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import four_point_transform


def _is_gui_available():
    try:
        cv2.namedWindow("__test__", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("__test__")
        return True
    except Exception:
        return False


GUI_AVAILABLE = _is_gui_available()


def process_p2_answers(image_path=None, show_images=False, save_images=False):
    """
    Xử lý nhận dạng mã đề từ ảnh p2 (đáp án 5 chữ số)
    
    Args:
        image_path (str): Đường dẫn đến file ảnh. Nếu None sẽ dùng "p21.jpg" mặc định
        show_images (bool): Có hiển thị ảnh hay không
        save_images (bool): Có lưu ảnh kết quả hay không
    
    Returns:
        list: Danh sách các mã đề được nhận dạng (mỗi mã đề 5 chữ số)
    """
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

    # Tìm contours đạt yêu cầu (4 góc, diện tích phù hợp)
    qualified_contours = []
    for i, contour in enumerate(contours):
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = cv2.contourArea(contour)
        
        if len(approx) == 4 and 120000 < area < 175000:
            qualified_contours.append((contour, approx, area, i))
            print(f"Contour {i}: 4 goc, dien tich = {area:.0f} pixels - DAT YEU CAU")

    print(f"Tong cong tim thay {len(qualified_contours)} contour dat yeu cau")

    if not qualified_contours:
        print("Khong tim thay contour nao dat yeu cau!")
        return []

    # Sắp xếp theo vị trí từ trên xuống dưới, trái sang phải
    def sort_contours_by_position(contours):
        contour_data = []
        for contour, approx, area, original_idx in contours:
            x, y, _, _ = cv2.boundingRect(contour)
            contour_data.append((contour, approx, area, original_idx, x, y))
        
        tolerance = 50
        contour_data.sort(key=lambda item: (item[5] // tolerance, item[4]))
        return [(item[0], item[1], item[2], item[3]) for item in contour_data]
    
    qualified_contours = sort_contours_by_position(qualified_contours)
    detected_answers = []
    
    # Xử lý từng contour
    for idx, (contour, approx, area, original_idx) in enumerate(qualified_contours):
        print(f"\n=== XU LY CONTOUR {idx + 1}/{len(qualified_contours)} ===")
        print(f"Contour {original_idx}: dien tich = {area:.0f} pixels")
        
        try:
            # Crop và xoay ảnh
            paper_points = approx.reshape(4, 2)
            cropped_paper = four_point_transform(cv2.imread(image_path), paper_points)
            cropped_paper = cv2.rotate(cropped_paper, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            # Cắt bên trái 55px
            cropped_paper = cropped_paper[:, 55:]
            print("  Da cat ben trai 55px")
            
            # Chia contour thành 2 phần bằng nhau (trái và phải)
            height, width = cropped_paper.shape[:2]
            mid_width = width // 2
            
            left_part = cropped_paper[:, :mid_width]
            right_part = cropped_paper[:, mid_width:]
            
            print(f"  Da chia thanh 2 phan: Trai ({left_part.shape[1]}px) va Phai ({right_part.shape[1]}px)")
            
            # Xử lý cả 2 phần
            parts = [("Trai", left_part), ("Phai", right_part)]
            all_detected_strings = []
            
            for part_idx, (part_name, part_image) in enumerate(parts):
                print(f"\n  --- XU LY PHAN {part_name.upper()} ---")
                
                # Thiết lập grid cho từng phần
                part_height, part_width = part_image.shape[:2]
                rows, cols = 6, 2
                cell_height, cell_width = part_height // rows, part_width // cols
                
                # Xử lý nhận dạng cho phần này
                gray_cropped = cv2.cvtColor(part_image, cv2.COLOR_BGR2GRAY)
                _, binary_otsu = cv2.threshold(gray_cropped, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Thu thập giá trị mean và tính ngưỡng thông minh (bỏ 2 hàng đầu)
                all_mean_values = []
                for col in range(0, cols):
                    for row in range(2, rows):
                        y1, y2 = row * cell_height, (row + 1) * cell_height
                        x1, x2 = col * cell_width, (col + 1) * cell_width
                        cell_binary = binary_otsu[y1:y2, x1:x2]
                        all_mean_values.append(np.mean(cell_binary))
                
                # Tim nguong thong minh bang cach phan tich khoang cach - TOI UU CHO 4 O
                sorted_values = sorted(all_mean_values)
                print(f"    Top 8 gia tri mean thap nhat cho phan {part_name}: {sorted_values[:8]}")
                
                # Tim khoang cach lon nhat giua cac gia tri mean (trong 6 gia tri dau - toi uu cho 4 o)
                max_gap = 0
                threshold_idx = 0
                gap_info = []
                
                for i in range(1, min(6, len(sorted_values))):
                    gap = sorted_values[i] - sorted_values[i-1]
                    gap_info.append((i, gap, sorted_values[i-1], sorted_values[i]))
                    if gap > max_gap:
                        max_gap = gap
                        threshold_idx = i
                
                print(f"    Phan tich khoang cach cho phan {part_name}:")
                for i, gap, val1, val2 in gap_info[:5]:  # Chi hien thi 5 gap dau
                    print(f"      Gap {i}: {gap:.3f} (giua {val1:.3f} va {val2:.3f})")
                
                # Su dung nguong thong minh voi dieu kien chat che hon cho 4 o
                if max_gap > 8 and threshold_idx <= 4:  # Giam nguong gap va gioi han vi tri
                    threshold = (sorted_values[threshold_idx-1] + sorted_values[threshold_idx]) / 2
                    print(f"    ✓ Su dung nguong thong minh cho phan {part_name}: {threshold:.3f}")
                    print(f"      Khoang cach lon nhat: {max_gap:.3f} tai vi tri {threshold_idx}")
                    print(f"      Gia tri truoc nguong: {sorted_values[threshold_idx-1]:.3f}")
                    print(f"      Gia tri sau nguong: {sorted_values[threshold_idx]:.3f}")
                else:
                    # Fallback ve percentile toi uu cho 4 o - GIA TRI THAP DE BAT NHIEU O HON
                    threshold = np.percentile(all_mean_values, 50)  # Tang tu 35% len 50% de bat nhieu o hon
                    print(f"    ⚠️ Su dung nguong percentile cho phan {part_name}: {threshold:.3f}")
                    print(f"      Khong tim thay khoang cach phu hop (max gap: {max_gap:.3f}, vi tri: {threshold_idx})")
                    
                    # Neu van it o qua, giam nguong xuong
                    temp_count = sum(1 for x in all_mean_values if x < threshold)
                    if temp_count < 2:  # Neu duoi 2 o thi giam nguong
                        threshold = np.percentile(all_mean_values, 60)  # Tang len 60%
                        print(f"      Chi co {temp_count} o duoi nguong, tang nguong len: {threshold:.3f}")
                        temp_count = sum(1 for x in all_mean_values if x < threshold)
                        if temp_count < 2:  # Neu van it, tang them
                            threshold = np.percentile(all_mean_values, 70)  # Tang len 70%
                            print(f"      Van chi co {temp_count} o, tang nguong len: {threshold:.3f}")
                
                print(f"    Gia tri mean thap nhat: {min(all_mean_values):.3f}")
                print(f"    Gia tri mean cao nhat: {max(all_mean_values):.3f}")
                print(f"    So luong gia tri mean duoi nguong: {sum(1 for x in all_mean_values if x < threshold)}")
                
                # Nhận dạng ô đã tô
                filled_cells = []
                numbered_image = part_image.copy() if show_images or save_images else None
                
                for col in range(0, cols):
                    for row in range(2, rows):
                        y1, y2 = row * cell_height, (row + 1) * cell_height
                        x1, x2 = col * cell_width, (col + 1) * cell_width
                        
                        cell_binary = binary_otsu[y1:y2, x1:x2]
                        mean_val = np.mean(cell_binary)
                        
                        if numbered_image is not None:
                            cv2.putText(numbered_image, str(row - 2), 
                                       (x1 + 2, y1 + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)
                            cv2.putText(numbered_image, f"{mean_val:.1f}", 
                                       (x1 + 2, y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 255, 255), 1)
                        
                        # Nhan dang o da to (mean thap = nhieu pixel den)
                        if mean_val < threshold:
                            filled_cells.append((col, row - 2, mean_val))
                            if numbered_image is not None:
                                cv2.rectangle(numbered_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
                            print(f"      ✓ O da to tai cot {col}, hang {row - 2} - Mean: {mean_val:.3f} < {threshold:.3f}")
                        else:
                            # Hien thi cac o gan nguong de debug
                            if abs(mean_val - threshold) < 5:
                                print(f"      - O gan nguong tai cot {col}, hang {row - 2} - Mean: {mean_val:.3f} >= {threshold:.3f}")
                
                # Tạo kết quả cho phần này - TOI UU CHO 4 O VỚI XỬ LÝ ÍT Ô
                filled_cells.sort(key=lambda x: x[2])  # Sắp xếp theo mean (thấp nhất trước)
                
                # Xu ly truong hop it o duoc nhan dang
                if len(filled_cells) < 2:
                    print(f"    Canh bao: Chi tim thay {len(filled_cells)} o da to, can tang nguong de tim them")
                    # Tang nguong de tim them o
                    higher_threshold = np.percentile(all_mean_values, 75)  # Tang len 75%
                    print(f"    Thu voi nguong cao hon: {higher_threshold:.3f}")
                    
                    # Tim lai cac o da to voi nguong cao hon
                    additional_cells = []
                    for col in range(0, cols):
                        for row in range(2, rows):
                            y1, y2 = row * cell_height, (row + 1) * cell_height
                            x1, x2 = col * cell_width, (col + 1) * cell_width
                            cell_binary = binary_otsu[y1:y2, x1:x2]
                            mean_val = np.mean(cell_binary)
                            
                            if mean_val < higher_threshold and (col, row - 2, mean_val) not in filled_cells:
                                additional_cells.append((col, row - 2, mean_val))
                                print(f"      + Them o tai cot {col}, hang {row - 2} - Mean: {mean_val:.3f}")
                    
                    # Ket hop va sap xep lai
                    filled_cells.extend(additional_cells)
                    filled_cells.sort(key=lambda x: x[2])
                    print(f"    Sau khi tang nguong: Tim them {len(additional_cells)} o, tong {len(filled_cells)} o")
                
                # Gioi han chi lay 4 o da to tot nhat
                if len(filled_cells) > 4:
                    print(f"    Canh bao: Tim thay {len(filled_cells)} o da to, chi lay 4 o tot nhat")
                    # Kiem tra xem co khoang cach lon giua o thu 4 va o thu 5 khong
                    if len(filled_cells) >= 5:
                        gap_4_5 = filled_cells[4][2] - filled_cells[3][2]
                        print(f"    Khoang cach giua o thu 4 va o thu 5: {gap_4_5:.3f}")
                        if gap_4_5 > 5:  # Neu co khoang cach ro ret thi chi lay 4 o dau
                            filled_cells = filled_cells[:4]
                            print("    Chi lay 4 o dau vi co khoang cach ro ret")
                        else:
                            filled_cells = filled_cells[:4]  # Van chi lay 4 o dau
                            print("    Chi lay 4 o dau (uu tien o co mean thap nhat)")
                    else:
                        filled_cells = filled_cells[:4]
                
                print(f"    Cac o da to trong phan {part_name} (sap xep theo mean):")
                for col, row, mean_val in filled_cells:
                    print(f"      Cot {col}, Hang {row}: {mean_val:.3f}")
                
                ans = [(col, row) for col, row, _ in filled_cells]
                print(f"    Ket qua phan {part_name}: Tim thay {len(ans)} o da to")
                
                ans.sort(key=lambda x: x[0])  # Sắp xếp theo cột
                part_string = ''.join([str(digit) for _, digit in ans])
                
                # Dien them so 0 phia truoc neu khong du cho phan nay (mong doi 2 chu so)
                expected_length = 2  # Mỗi phần mong đợi 2 chữ số
                if len(part_string) < expected_length:
                    original_length = len(part_string)
                    part_string = part_string.zfill(expected_length)
                    print(f"    Dap an goc phan {part_name}: {original_length} chu so -> Da dien them {expected_length - original_length} so 0 phia truoc")
                elif len(part_string) > expected_length:
                    print(f"    Canh bao: Phan {part_name} co {len(part_string)} chu so (nhieu hon {expected_length} mong doi)")
                    # Cat bot neu qua nhieu (lay 2 chu so dau)
                    part_string = part_string[:expected_length]
                    print(f"    Da cat xuong con {expected_length} chu so: {part_string}")
                
                # Lưu và hiển thị nếu cần
                if save_images and numbered_image is not None:
                    cv2.imwrite(f"numbered_{idx + 1}_{original_idx}_{part_name.lower()}.jpg", numbered_image)
                    print(f"    Da luu anh phan {part_name} vao file 'numbered_{idx + 1}_{original_idx}_{part_name.lower()}.jpg'")
                
                if show_images and numbered_image is not None and GUI_AVAILABLE:
                    try:
                        cv2.imshow(f"Phan {part_name} - Vung {idx + 1}", numbered_image)
                        cv2.waitKey(0)
                        cv2.destroyAllWindows()
                    except Exception:
                        global GUI_AVAILABLE
                        GUI_AVAILABLE = False
                        cv2.imwrite(f"numbered_{idx + 1}_{original_idx}_{part_name.lower()}.jpg", numbered_image)
                        print(f"    GUI khong kha dung, da luu 'numbered_{idx + 1}_{original_idx}_{part_name.lower()}.jpg'")
                elif show_images and numbered_image is not None and not GUI_AVAILABLE:
                    cv2.imwrite(f"numbered_{idx + 1}_{original_idx}_{part_name.lower()}.jpg", numbered_image)
                    print(f"    GUI khong kha dung, da luu 'numbered_{idx + 1}_{original_idx}_{part_name.lower()}.jpg'")
                
                print(f"    Ket qua phan {part_name}: {part_string} ✓ ({len(part_string)} chu so)")
                print(f"    Cac o da to phan {part_name}:", ans)
                all_detected_strings.append(part_string)
            
            # Kết hợp kết quả từ cả 2 phần - TOI UU CHO 4 CHU SO TONG
            contour_string = ''.join(all_detected_strings)
            
            # Dam bao ket qua co 4 chu so
            if len(contour_string) < 4:
                original_length = len(contour_string)
                contour_string = contour_string.zfill(4)  # Điền 0 phía trước để đủ 4 chữ số
                print(f"  Dap an tong: {original_length} chu so -> Da dien them {4 - original_length} so 0 phia truoc")
            elif len(contour_string) > 4:
                print(f"  Canh bao: Tong co {len(contour_string)} chu so (nhieu hon 4 mong doi)")
                # Cat bot neu qua nhieu (lay 4 chu so dau)
                contour_string = contour_string[:4]
                print(f"  Da cat xuong con 4 chu so: {contour_string}")
            
            # Kết quả - luon mong doi 4 chu so
            print(f"Dap An CONTOUR {idx + 1}: {contour_string} ✓ (4 chu so)")
            detected_answers.append(contour_string)
            
        except Exception as e:
            print(f"Loi khi xu ly contour {idx + 1}: {e}")
            continue
    
    return detected_answers


def main():
    """Hàm main để test"""
    answers = process_p2_answers(show_images=GUI_AVAILABLE, save_images=True)
    print(f"\nKet qua cuoi cung: {answers}")


if __name__ == "__main__":
    main()
