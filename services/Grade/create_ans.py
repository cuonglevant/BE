def score_answers(scanned_ans, correct_ans):
	"""
	So sánh đáp án quét với đáp án đúng, trả về điểm số thang 10.
	Args:
		scanned_ans (list): đáp án quét được [(câu, đáp án), ...]
		correct_ans (list): đáp án đúng [(câu, đáp án), ...]
	Returns:
		float: điểm số thang 10
	"""
	if not scanned_ans or not correct_ans:
		return 0.0
	# Tạo dict để tra cứu đáp án đúng
	correct_dict = dict(correct_ans)
	total_questions = len(correct_ans)
	correct_count = 0
	for q, a in scanned_ans:
		if q in correct_dict and a == correct_dict[q]:
			correct_count += 1
	# Tính điểm thang 10
	score = round((correct_count / total_questions) * 10, 2) if total_questions > 0 else 0.0
	return score

from services.Process.p1 import process_p1_answers
from services.Process.p2 import process_p2_answers
from services.Process.p3 import process_p3_answers

def scan_all_answers(p1_img, p2_img, p3_img, show_images=False, save_images=False):
	"""
	Quét đáp án từ 3 phần và trả về mảng đáp án hoàn chỉnh.
	Args:
		p1_img, p2_img, p3_img: đường dẫn ảnh từng phần
	Returns:
		list: Mảng đáp án tổng hợp từ 3 phần
	"""
	ans_p1 = process_p1_answers(p1_img, show_images, save_images)
	ans_p2 = process_p2_answers(p2_img, show_images, save_images)
	ans_p3 = process_p3_answers(p3_img, show_images, save_images)
	# Gộp đáp án các phần lại
	all_ans = []
	if isinstance(ans_p1, list):
		all_ans.extend(ans_p1)
	if isinstance(ans_p2, list):
		all_ans.extend(ans_p2)
	if isinstance(ans_p3, list):
		all_ans.extend(ans_p3)
	return all_ans
