"""
Validation utilities for the Exam Grading System
"""


def validate_email(email):
    """Validate email format"""
    if not email or '@' not in email:
        return False, "Invalid email format"
    return True, None


def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password required"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    return True, None


def validate_student_id(student_id):
    """Validate student ID format (8 digits)"""
    if not student_id:
        return False, "Student ID required"
    if not isinstance(student_id, str):
        student_id = str(student_id)
    if not student_id.isdigit():
        return False, "Student ID must contain only digits"
    if len(student_id) != 8:
        return False, "Student ID must be 8 digits"
    return True, None


def validate_exam_code(exam_code):
    """Validate exam code format (4 digits)"""
    if not exam_code:
        return False, "Exam code required"
    if not isinstance(exam_code, str):
        exam_code = str(exam_code)
    if not exam_code.isdigit():
        return False, "Exam code must contain only digits"
    if len(exam_code) != 4:
        return False, "Exam code must be 4 digits"
    return True, None


def validate_score(score):
    """Validate score value (0-10)"""
    if score is None:
        return False, "Score required"
    try:
        score_float = float(score)
        if score_float < 0 or score_float > 10:
            return False, "Score must be between 0 and 10"
        return True, None
    except (ValueError, TypeError):
        return False, "Invalid score format"


def validate_answers(answers):
    """Validate answers list format"""
    if not answers:
        return False, "Answers required"
    if not isinstance(answers, list):
        return False, "Answers must be a list"
    if len(answers) == 0:
        return False, "Answers list cannot be empty"
    
    # Validate each answer is a tuple/list with 2 elements
    for i, answer in enumerate(answers):
        if not isinstance(answer, (list, tuple)):
            return False, f"Answer {i} must be a list or tuple"
        if len(answer) != 2:
            return False, f"Answer {i} must have 2 elements [question, choice]"
        question, choice = answer
        if not isinstance(question, int) or question < 1:
            return False, f"Question number must be positive integer"
        if not isinstance(choice, str) or choice not in ['A', 'B', 'C', 'D', '']:
            return False, f"Choice must be A, B, C, D, or empty"
    
    return True, None


def validate_image_file(file):
    """Validate uploaded image file"""
    if not file:
        return False, "No file provided"
    
    if file.filename == '':
        return False, "Empty filename"
    
    # Check file extension
    allowed_extensions = {'jpg', 'jpeg', 'png', 'bmp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    
    if ext not in allowed_extensions:
        return False, f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
    
    return True, None


def validate_session_id(session_id):
    """Validate session ID format (UUID)"""
    if not session_id:
        return False, "Session ID required"
    
    # Basic UUID format check
    if not isinstance(session_id, str):
        return False, "Invalid session ID format"
    
    parts = session_id.split('-')
    if len(parts) != 5:
        return False, "Invalid session ID format"
    
    return True, None


def validate_object_id(object_id):
    """Validate MongoDB ObjectId format"""
    if not object_id:
        return False, "Object ID required"
    
    if not isinstance(object_id, str):
        return False, "Invalid object ID format"
    
    if len(object_id) != 24:
        return False, "Object ID must be 24 characters"
    
    # Check if hex
    try:
        int(object_id, 16)
        return True, None
    except ValueError:
        return False, "Invalid object ID format"


def sanitize_input(text, max_length=1000):
    """Sanitize text input"""
    if not text:
        return ""
    
    text = str(text).strip()
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text
