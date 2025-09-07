import cv2
import math
import numpy as np
import random
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import find_corner_by_rotated_rect, four_point_transform, sort_contours


def process_p3_answers(image_path=None, show_images=False, save_images=False):
    """
    Xử lý nhận dạng đáp án từ ảnh p3 (đáp án 10 chữ số)
    
    Args:
        image_path (str): Đường dẫn đến file ảnh. Nếu None sẽ dùng "p21.jpg" mặc định
        show_images (bool): Có hiển thị ảnh hay không
        save_images (bool): Có lưu ảnh kết quả hay không
    
    Returns:
        list: Danh sách các mã đáp án được nhận dạng (mỗi mã đáp án 10 chữ số)
    """
    # 1. Doc anh, chuyen thanh anh xam
    if image_path is None:
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p23.jpg")
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Không thể đọc file ảnh: {image_path}")
        return []
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2. Nhan dang vung dap an trong anh
    # Phat hien canh bang Canny edge detection
    edged = cv2.Canny(blurred, 75, 200)

    # Tim tat ca cac contour trong anh
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Ve tat ca cac contour tim duoc
    all_contours_image = image.copy()
    print(f"Tim thay {len(contours)} contours")

    # Danh sách kết quả
    detected_answers = []

    # Ve tung contour voi mau sac ngau nhien va hien thi dien tich
    large_contours_count = 0
    for i, contour in enumerate(contours):
        # Tinh dien tich
        area = cv2.contourArea(contour)
        
        print(f"Contour {i}: Dien tich = {area:.0f} pixels")
        
        # Chi ve contour co dien tich lon hon 120000
        if area > 120000:
            # Tao mau ngau nhien cho moi contour
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            
            # Ve contour
            cv2.drawContours(all_contours_image, [contour], -1, color, 3)
            
            # Tim trung tam contour de ve text
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # Ve text dien tich
                cv2.putText(all_contours_image, f"{i}: {area:.0f}", 
                           (cx, cy), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            large_contours_count += 1
            print(f"  -> Ve contour {i} (dien tich lon)")

    # Luu anh tat ca contours lon
    if save_images:
        cv2.imwrite("all_contours_p3.jpg", all_contours_image)
        print(f"Da luu {large_contours_count} contours lon vao file 'all_contours_p3.jpg'")

    # Sap xep cac contour theo dien tich giam dan
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # Tim va hien thi tat ca cac contour co 4 goc dap ung dieu kien
    qualified_contours = []
    qualified_image = image.copy()

    print("\n--- TIM KIEM CAC CONTOUR CO 4 GOC ---")
    for i, contour in enumerate(contours):
        # Tinh chu vi cua contour
        perimeter = cv2.arcLength(contour, True)
        # Xu ly don gian contour
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = cv2.contourArea(contour)
        
        # Neu contour co 4 goc va dien tich du lon
        if len(approx) == 4 and area > 200000 and area < 260000:
            qualified_contours.append((contour, approx, area, i))
            print(f"Contour {i}: 4 goc, dien tich = {area:.0f} pixels - DAT YEU CAU")
            
            # Ve contour len anh
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            cv2.drawContours(qualified_image, [approx], -1, color, 3)
            
            # Ve so thu tu va dien tich
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(qualified_image, f"#{len(qualified_contours)}: {area:.0f}", 
                           (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        elif len(approx) == 4:
            print(f"Contour {i}: 4 goc, dien tich = {area:.0f} pixels - DIEN TICH KHONG PHU HOP")
        elif area > 150000:
            print(f"Contour {i}: {len(approx)} goc, dien tich = {area:.0f} pixels - KHONG PHAI 4 GOC")

    print(f"\nTong cong tim thay {len(qualified_contours)} contour dat yeu cau")

    # Luu anh cac contours dat yeu cau
    if save_images:
        cv2.imwrite("qualified_contours_p3.jpg", qualified_image)
        print(f"Da luu {len(qualified_contours)} contours dat yeu cau vao file 'qualified_contours_p3.jpg'")

    # Xu ly tat ca cac contour dat yeu cau
    if qualified_contours:
        # Sap xep theo vi tri tu tren xuong duoi (theo y nho nhat cua contour, tang dan)
        qualified_contours.sort(key=lambda x: cv2.boundingRect(x[0])[1])
        
        print("\n--- DANH SACH CAC CONTOUR DAT YEU CAU (SAP XEP THEO Y) ---")
        for idx, (contour, approx, area, original_idx) in enumerate(qualified_contours):
            x, y, w, h = cv2.boundingRect(contour)
            print(f"{idx + 1}. Contour {original_idx}: x={x}, y={y}, dien tich = {area:.0f} pixels")
        
        print(f"\nSE XU LY TAT CA {len(qualified_contours)} CONTOURS")
        
        # Xu ly tung contour
        for idx, (contour, approx, area, original_idx) in enumerate(qualified_contours):
            print(f"\n=== XU LY CONTOUR {idx + 1}/{len(qualified_contours)} ===")
            print(f"Contour {original_idx}: dien tich = {area:.0f} pixels")
            
            # Ve contour len anh goc de kiem tra
            final_image = cv2.imread(image_path).copy()
            cv2.drawContours(final_image, [approx], -1, (0, 255, 0), 3)
            
            # Crop vung dap an bang perspective transform
            paper_points = approx.reshape(4, 2)
            
            try:
                # Su dung four_point_transform de crop dap an
                cropped_paper = four_point_transform(cv2.imread(image_path), paper_points)
                
                # Xoay anh 90 do nguoc chieu kim dong ho
                cropped_paper = cv2.rotate(cropped_paper, cv2.ROTATE_90_COUNTERCLOCKWISE)
                
                # Cat 20px moi ben truoc khi chia thanh luoi
                height, width = cropped_paper.shape[:2]
                crop_margin = 25
                h_crop_margin = 10
                cropped_paper = cropped_paper[crop_margin:height-h_crop_margin, crop_margin:width-crop_margin]
                print(f"  Da cat 20px moi ben: {width}x{height} -> {cropped_paper.shape[1]}x{cropped_paper.shape[0]}")
                
                # Chia anh thanh luoi
                height, width = cropped_paper.shape[:2]
                grid_image = cropped_paper.copy()
                
                rows = 13
                cols = 5
                
                # Tinh kich thuoc moi o
                cell_height = height // rows
                cell_width = width // cols
                
                # Ve cac duong ngang
                for i in range(1, rows):
                    y = i * cell_height
                    cv2.line(grid_image, (0, y), (width, y), (0, 255, 0), 2)
                
                # Ve cac duong doc
                for j in range(1, cols):
                    x = j * cell_width
                    cv2.line(grid_image, (x, 0), (x, height), (0, 255, 0), 2)
                
                if save_images:
                    cv2.imwrite(f"cropped_p3_{idx + 1}_{original_idx}.jpg", cropped_paper)
                    cv2.imwrite(f"grid_p3_{idx + 1}_{original_idx}.jpg", grid_image)
                    print(f"Da luu anh da crop vao file 'cropped_p3_{idx + 1}_{original_idx}.jpg'")
                    print(f"Da luu luoi vao file 'grid_p3_{idx + 1}_{original_idx}.jpg'")
                    print(f"Chia thanh luoi {rows}x{cols} = {rows*cols} o")
                    print(f"Kich thuoc moi o: {cell_width}x{cell_height} pixels")
                
                # NHAN DANG dap an BANG OTSU THRESHOLD VA MEAN
                gray_cropped = cv2.cvtColor(cropped_paper, cv2.COLOR_BGR2GRAY)
                numbered_image = grid_image.copy()
                
                # Ap dung Otsu threshold
                _, binary_otsu = cv2.threshold(gray_cropped, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                if save_images:
                    cv2.imwrite(f"debug_otsu_p3_{idx + 1}_{original_idx}.jpg", binary_otsu)
                
                print(f"  Nhan dang {(rows-1)*(cols-1)} o (bo hang 1 va cot 1) bang Otsu threshold...")
                
                ans = []
                all_mean_values = []
                
                # Thu thap gia tri mean cua tat ca cac o
                for col in range(1, cols):
                    for row in range(1, rows):
                        x1 = col * cell_width
                        y1 = row * cell_height
                        x2 = x1 + cell_width
                        y2 = y1 + cell_height
                        
                        # Lay vung o tu anh binary
                        cell_binary = binary_otsu[y1:y2, x1:x2]
                        
                        # Tinh gia tri mean (0 = den, 255 = trang)
                        mean_val = np.mean(cell_binary)
                        all_mean_values.append(mean_val)
                
                # Tim nguong thong minh bang cach phan tich khoang cach
                sorted_values = sorted(all_mean_values)
                print(f"  Top 10 gia tri mean thap nhat: {sorted_values[:10]}")
                
                # Tim khoang cach lon nhat giua cac gia tri mean (trong 15 gia tri dau)
                max_gap = 0
                threshold_idx = 0
                gap_info = []
                
                for i in range(1, min(15, len(sorted_values))):
                    gap = sorted_values[i] - sorted_values[i-1]
                    gap_info.append((i, gap, sorted_values[i-1], sorted_values[i]))
                    if gap > max_gap:
                        max_gap = gap
                        threshold_idx = i
                
                print("  Phan tich khoang cach giua cac gia tri:")
                for i, gap, val1, val2 in gap_info[:10]:  # Chi hien thi 10 gap dau
                    print(f"    Gap {i}: {gap:.3f} (giua {val1:.3f} va {val2:.3f})")
                
                # Su dung nguong thong minh neu co khoang cach lon
                if max_gap > 15:  # Nguong khoang cach toi thieu
                    threshold = (sorted_values[threshold_idx-1] + sorted_values[threshold_idx]) / 2
                    print(f"  ✓ Su dung nguong thong minh: {threshold:.3f}")
                    print(f"    Khoang cach lon nhat: {max_gap:.3f} tai vi tri {threshold_idx}")
                    print(f"    Gia tri truoc nguong: {sorted_values[threshold_idx-1]:.3f}")
                    print(f"    Gia tri sau nguong: {sorted_values[threshold_idx]:.3f}")
                else:
                    # Fallback ve percentile neu khong co khoang cach ro rang
                    threshold = np.percentile(all_mean_values, 8.55)
                    print(f"  ⚠️ Su dung nguong percentile: {threshold:.3f}")
                    print(f"    Khong tim thay khoang cach lon (max gap: {max_gap:.3f})")
                
                print(f"  Gia tri mean thap nhat: {min(all_mean_values):.3f}")
                print(f"  Gia tri mean cao nhat: {max(all_mean_values):.3f}")
                print(f"  So luong gia tri mean duoi nguong: {sum(1 for x in all_mean_values if x < threshold)}")
                
                # Nhan dang cac o da to
                filled_cells = []
                for col in range(1, cols):
                    for row in range(1, rows):
                        x1 = col * cell_width
                        y1 = row * cell_height
                        x2 = x1 + cell_width
                        y2 = y1 + cell_height
                        
                        # Lay vung o tu anh binary
                        cell_binary = binary_otsu[y1:y2, x1:x2]
                        
                        # Tinh gia tri mean
                        mean_val = np.mean(cell_binary)
                        
                        # Hien thi thong tin debug chi tiet hon
                        cv2.putText(numbered_image, str(row - 1), 
                                   (x1 + 2, y1 + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)
                        cv2.putText(numbered_image, f"{mean_val:.1f}", 
                                   (x1 + 2, y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 255, 255), 1)
                        
                        # Nhan dang o da to (mean thap = nhieu pixel den)
                        if mean_val < threshold:
                            filled_cells.append((col, row - 1, mean_val))
                            cv2.rectangle(numbered_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
                            print(f"    ✓ O da to tai cot {col}, hang {row - 1} - Mean: {mean_val:.3f} < {threshold:.3f}")
                        else:
                            # Hien thi cac o gan nguong de debug
                            if abs(mean_val - threshold) < 5:
                                print(f"    - O gan nguong tai cot {col}, hang {row - 1} - Mean: {mean_val:.3f} >= {threshold:.3f}")
                
                # Sap xep cac o da to theo mean (thap nhat truoc)
                filled_cells.sort(key=lambda x: x[2])
                print("  Cac o da to (sap xep theo mean):")
                for col, row, mean_val in filled_cells:
                    print(f"    Cot {col}, Hang {row}: {mean_val:.3f}")
                
                ans = [(col, row) for col, row, _ in filled_cells]
                
                print(f"  Ket qua: Tim thay {len(ans)} o da to")
                
                # Sap xep theo cot va tao dap an
                ans.sort(key=lambda x: x[0])
                contour_string = ''.join([str(digit) for _, digit in ans])
                
                # Luu anh co danh so
                if save_images:
                    cv2.imwrite(f"numbered_p3_{idx + 1}_{original_idx}.jpg", numbered_image)
                    print(f"Da luu anh co danh so vao file 'numbered_p3_{idx + 1}_{original_idx}.jpg'")
                
                # In ket qua dap an
                if len(contour_string) == 10:
                    print(f"Dap An CONTOUR {idx + 1}: {contour_string} ✓")
                    detected_answers.append(contour_string)
                else:
                    print(f"Dap an CONTOUR {idx + 1}: {contour_string} ({len(contour_string)} chu so) ⚠️")
                    print("Cac o da to:", ans)
                    detected_answers.append(contour_string)  # Vẫn thêm vào dù không đủ 10 số
                
                # Hien thi anh co danh so thay vi anh crop
                if show_images:
                    cv2.imshow(f"Vung {idx + 1} co danh so", numbered_image)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                
            except Exception as e:
                print(f"Loi khi xu ly contour {idx + 1}: {e}")
                continue

    else:
        print("Khong tim thay contour nao dat yeu cau!")
    
    return detected_answers


def main():
    """Hàm main để test"""
    answers = process_p3_answers(show_images=True, save_images=True)
    print(f"\nKet qua cuoi cung: {answers}")


if __name__ == "__main__":
    main()
