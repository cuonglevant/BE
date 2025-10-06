
class CorrectAns:
	def __init__(self, id: str, answers: list):
		self.id = id
		self.answers = answers

	def to_dict(self):
		return {
			'id': self.id,
			'answers': self.answers
		}
