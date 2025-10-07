from datetime import datetime
from bson import ObjectId


class Exam:
    def __init__(self, exam_code: str, score_p1: float = 0.0,
                 score_p2: float = 0.0, score_p3: float = 0.0,
                 total_score: float = 0.0, created_at: datetime = None,
                 created_by: ObjectId = None, correct_ans: ObjectId = None):
        self.exam_code = exam_code
        self.score_p1 = score_p1
        self.score_p2 = score_p2
        self.score_p3 = score_p3
        self.total_score = total_score
        self.created_at = created_at or datetime.now()
        self.created_by = created_by  # ObjectId của user
        self.correct_ans = correct_ans  # ObjectId của correctans

    def to_dict(self):
        data = {
            'exam_code': self.exam_code,
            'score_p1': self.score_p1,
            'score_p2': self.score_p2,
            'score_p3': self.score_p3,
            'total_score': self.total_score,
            'created_at': self.created_at.isoformat(),
            'created_by': str(self.created_by) if self.created_by else None,
            'correct_ans': str(self.correct_ans) if self.correct_ans else None
        }
        return data
