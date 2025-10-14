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
            # Allow both flattened list-of-tuples and dict-per-question formats.
            # Normalize to flat dict: key -> bool
            def normalize_p2(items):
                if isinstance(items, list):
                    # Expect list of tuples [("q1_a", True/False), ...]
                    return dict(items)
                elif isinstance(items, dict):
                    flat = {}
                    for q, answers in items.items():
                        for opt, val in (answers or {}).items():
                            flat[f"q{q}_{opt}"] = bool(val)
                    return flat
                else:
                    return {}

            scanned_flat = normalize_p2(p2_scanned)
            correct_flat = normalize_p2(p2_correct)

            keys = set(correct_flat.keys())
            total_questions = len(keys) if keys else max(len(scanned_flat), len(correct_flat))
            correct_count = sum(1 for k in keys if scanned_flat.get(k) == correct_flat.get(k))

            p2_score = (correct_count / total_questions) * 10 if total_questions else 0.0
            scores['p2_score'] = round(p2_score, 2)
        else:
            scores['p2_score'] = 0.0
    else:
        scores['p2_score'] = 0.0

    # Score P3 (Numerical values, 10 points total) - tolerates both old mark-list and numeric formats
    if 'p3' in scanned_ans and 'p3' in correct_ans:
        p3_scanned = scanned_ans['p3']
        p3_correct = correct_ans['p3']

        if p3_scanned and p3_correct:
            # Normalize into dict: qid -> numeric or list/tuple
            def to_map(items):
                if isinstance(items, list):
                    return {k: v for k, v in items}
                elif isinstance(items, dict):
                    return dict(items)
                return {}

            correct_dict = to_map(p3_correct)
            total_questions = len(p3_correct)
            correct_count = 0

            for qid, val in (p3_scanned if isinstance(p3_scanned, list) else p3_scanned.items()):
                if qid in correct_dict:
                    exp = correct_dict[qid]
                    # If both numeric, compare with tolerance
                    if isinstance(val, (int, float)) and isinstance(exp, (int, float)):
                        if abs(float(val) - float(exp)) < 0.01:
                            correct_count += 1
                    # If lists (old format), check subset
                    elif isinstance(val, (list, tuple)) and isinstance(exp, (list, tuple)):
                        if set(exp).issubset(set(val)):
                            correct_count += 1
                    # Fallback: direct equality
                    elif val == exp:
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

from services.Process.balanced_grid_omr import BalancedGridOMR
from services.Process.balanced_grid_p2 import BalancedGridP2
from services.Process.balanced_grid_p3 import BalancedGridP3


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
    # P1
    p1 = BalancedGridOMR()
    p1_res = p1.process_part1(p1_img)
    p1_list = []
    for item in (p1_res.get('answers') or []):
        # Convert to (question, answer)
        q = item.get('question')
        a = item.get('answer')
        if q is not None and a is not None:
            p1_list.append((int(q), str(a)))

    # P2
    p2 = BalancedGridP2()
    p2_res = p2.process_part2(p2_img)
    p2_list = []
    for item in (p2_res.get('answers') or []):
        q = item.get('question')
        ans_map = item.get('answers') or {}
        for opt in ['a', 'b', 'c', 'd']:
            if opt in ans_map:
                p2_list.append((f"q{int(q)}_{opt}", bool(ans_map[opt])))

    # P3
    p3 = BalancedGridP3(debug_mode=False)
    p3_res = p3.process_part3(p3_img)
    p3_list = []
    for item in (p3_res.get('answers') or []):
        q = item.get('question')
        val = item.get('answer')
        if q is not None and val is not None:
            p3_list.append((int(q), float(val)))

    return {
        'p1': p1_list,
        'p2': p2_list,
        'p3': p3_list
    }
