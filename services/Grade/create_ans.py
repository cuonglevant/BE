def score_answers(scanned_ans, correct_ans):
    """
    Compare scanned answers with correct answers for all exam parts.

    Args:
        scanned_ans (dict): Scanned answers {
            'p1': [(1, 'A'), (2, 'B'), ...],  # 40 ABCD answers
            'p2': [('p2_c1_a', 'Dung'), ...],  # True/False answers
            'p3': [('p3_c1', [1,3,5]), ...]    # Essay marked rows
        }
        correct_ans (dict): Correct answers in same format

    Returns:
        dict: {
            'p1_score': float (out of 10),
            'p2_score': float (out of 10),
            'p3_score': float (out of 10),
            'total_score': float (out of 10)
        }
    """
    if not scanned_ans or not correct_ans:
        return {
            'p1_score': 0.0,
            'p2_score': 0.0,
            'p3_score': 0.0,
            'total_score': 0.0
        }

    scores = {}

    # Score P1 (40 questions, 10 points total)
    if 'p1' in scanned_ans and 'p1' in correct_ans:
        p1_scanned = scanned_ans['p1']
        p1_correct = correct_ans['p1']

        if p1_scanned and p1_correct:
            correct_dict = dict(p1_correct)
            total_questions = len(p1_correct)
            correct_count = 0

            for q, a in p1_scanned:
                if q in correct_dict and a == correct_dict[q]:
                    correct_count += 1

            p1_score = (correct_count / total_questions) * 10
            scores['p1_score'] = round(p1_score, 2)
        else:
            scores['p1_score'] = 0.0
    else:
        scores['p1_score'] = 0.0

    # Score P2 (True/False sub-questions, 10 points total)
    if 'p2' in scanned_ans and 'p2' in correct_ans:
        p2_scanned = scanned_ans['p2']
        p2_correct = correct_ans['p2']

        if p2_scanned and p2_correct:
            correct_dict = dict(p2_correct)
            total_questions = len(p2_correct)
            correct_count = 0

            for qid, a in p2_scanned:
                if qid in correct_dict and a == correct_dict[qid]:
                    correct_count += 1

            p2_score = (correct_count / total_questions) * 10
            scores['p2_score'] = round(p2_score, 2)
        else:
            scores['p2_score'] = 0.0
    else:
        scores['p2_score'] = 0.0

    # Score P3 (Essay symbols, 10 points total)
    if 'p3' in scanned_ans and 'p3' in correct_ans:
        p3_scanned = scanned_ans['p3']
        p3_correct = correct_ans['p3']

        if p3_scanned and p3_correct:
            correct_dict = {qid: marks for qid, marks in p3_correct}
            total_questions = len(p3_correct)
            correct_count = 0

            for qid, marks in p3_scanned:
                if qid in correct_dict:
                    # Consider correct if all expected marks are present
                    expected_marks = set(correct_dict[qid])
                    scanned_marks = set(marks)
                    if expected_marks.issubset(scanned_marks):
                        correct_count += 1

            p3_score = (correct_count / total_questions) * 10
            scores['p3_score'] = round(p3_score, 2)
        else:
            scores['p3_score'] = 0.0
    else:
        scores['p3_score'] = 0.0

    # Calculate total score (average of all parts)
    total = scores['p1_score'] + scores['p2_score'] + scores['p3_score']
    scores['total_score'] = round(total / 3, 2)

    return scores


from services.Process.p1 import process_p1_answers
from services.Process.p2 import process_p2_answers
from services.Process.p3 import process_p3_answers


def scan_all_answers(p1_img, p2_img, p3_img,
                     show_images=False, save_images=False):
    """
    Scan answers from all 3 exam sections.

    PHẦN I: Standard ABCD (40 questions)
    PHẦN II: True/False format (multiple sub-questions)
    PHẦN III: Essay/Multi-row format (8 columns)

    Args:
        p1_img, p2_img, p3_img: Image paths for each section
        show_images: Display images (disabled)
        save_images: Save processed images

    Returns:
        dict: {
            'p1': [(1, 'A'), (2, 'B'), ...],  # 40 ABCD answers
            'p2': [('p2_q1_a', 'Dung'), ('p2_q2_a', 'Sai'), ...],  # True/False answers (sequential)
            'p3': [('p3_c1', [1,3,5]), ('p3_c2', [2,4]), ...]    # Essay marked rows (row numbers)
        }
    """
    ans_p1 = process_p1_answers(p1_img, show_images, save_images)
    ans_p2 = process_p2_answers(p2_img, show_images, save_images)
    ans_p3 = process_p3_answers(p3_img, show_images, save_images)

    return {
        'p1': ans_p1 if isinstance(ans_p1, list) else [],
        'p2': ans_p2 if isinstance(ans_p2, list) else [],
        'p3': ans_p3 if isinstance(ans_p3, list) else []
    }
