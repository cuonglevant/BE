"""
Backend API for Exam Grading System
Handles exam scanning, grading, and CRUD operations
"""
import os
import uuid
import tempfile
import logging
import time
import atexit
import shutil
from datetime import datetime, timedelta
from functools import lru_cache

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_swagger_ui import get_swaggerui_blueprint

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Swagger UI configuration
SWAGGER_URL = '/docs'
API_URL = '/static/swagger.json'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Exam Grading API"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import models and services
from Models.exam import Exam
from Models.correctans import CorrectAns
from services.Auth.auth_service import AuthService
from services.Db.exam_db_service import ExamDbService
from services.Db.correctans_db_service import CorrectAnsDbService
from services.Grade.create_ans import score_answers, scan_all_answers
from services.Grade.scan_student_id import scan_exam_code

# Redis setup (optional)
USE_REDIS = False
redis_client = None
scan_sessions = {}

try:
    import redis
    redis_client = redis.Redis(
        host='localhost', port=6379, decode_responses=True
    )
    redis_client.ping()
    USE_REDIS = True
    logger.info("Redis connected successfully")
except Exception as e:
    logger.warning(f"Redis not available ({e}), using in-memory session storage")
    scan_sessions = {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_session_temp_dir(session_id):
    """Create and return temp directory for session"""
    temp_dir = os.path.join(tempfile.gettempdir(), f"exam_{session_id}")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def cleanup_temp_files():
    """Cleanup all temporary session directories"""
    temp_root = tempfile.gettempdir()
    for dir_name in os.listdir(temp_root):
        if dir_name.startswith("exam_"):
            dir_path = os.path.join(temp_root, dir_name)
            shutil.rmtree(dir_path, ignore_errors=True)
            logger.info(f"Cleaned up: {dir_name}")


atexit.register(cleanup_temp_files)


def get_session_data(session_id):
    """Get session data from Redis or memory"""
    if USE_REDIS:
        data = redis_client.hgetall(f"session:{session_id}")
        return data if data else None
    else:
        return scan_sessions.get(session_id)


def set_session_data(session_id, key, value):
    """Set session data in Redis or memory"""
    if USE_REDIS:
        redis_client.hset(f"session:{session_id}", key, str(value))
        redis_client.expire(f"session:{session_id}", 1800)  # 30 minutes
    else:
        if session_id not in scan_sessions:
            scan_sessions[session_id] = {}
        scan_sessions[session_id][key] = str(value)


def delete_session(session_id):
    """Delete session and cleanup temp files"""
    if USE_REDIS:
        redis_client.delete(f"session:{session_id}")
    else:
        scan_sessions.pop(session_id, None)
    
    temp_dir = get_session_temp_dir(session_id)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


def save_uploaded_file(file, session_id, prefix):
    """Save uploaded file to temp directory"""
    filename = secure_filename(file.filename)
    temp_dir = get_session_temp_dir(session_id)
    filepath = os.path.join(temp_dir, f"{prefix}_{filename}")
    file.save(filepath)
    return filepath


@lru_cache(maxsize=100)
def get_cached_correct_answers(exam_code):
    """Get correct answers with caching"""
    return CorrectAnsDbService.get_correct_ans_by_exam_code(exam_code)


# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.before_request
def before_request():
    """Log incoming requests"""
    g.start_time = time.time()
    logger.info(f"→ {request.method} {request.path} from "
                f"{request.remote_addr}")


@app.after_request
def after_request(response):
    """Log response time"""
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        logger.info(f"← {response.status_code} - {elapsed:.3f}s")
    return response


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/auth/signup', methods=['POST'])
def signup():
    """Register new user"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    result = AuthService.sign_up(email, password)
    status = 201 if 'user' in result else 400
    return jsonify(result), status


@app.route('/auth/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    result = AuthService.login(email, password)
    status = 200 if 'user' in result else 401
    return jsonify(result), status


@app.route('/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    result = AuthService.logout(email)
    return jsonify(result)


# ============================================================================
# EXAM SESSION ENDPOINTS (Simplified flow)
# ============================================================================

@app.route('/exam/session/start', methods=['POST'])
def start_exam_session():
    """Start new exam grading session"""
    session_id = str(uuid.uuid4())
    set_session_data(session_id, 'created_at', datetime.now().isoformat())
    set_session_data(session_id, 'status', 'started')
    
    logger.info(f"Started session: {session_id}")
    return jsonify({'session_id': session_id}), 201


@app.route('/exam/session/exam_code', methods=['POST'])
def upload_exam_code():
    """Upload exam code image to identify which exam to grade"""
    session_id = request.form.get('session_id')
    
    if not session_id or not get_session_data(session_id):
        return jsonify({'error': 'Invalid session'}), 400
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        file = request.files['image']
        filepath = save_uploaded_file(file, session_id, 'exam_code')
        exam_code = scan_exam_code(filepath)
        
        set_session_data(session_id, 'exam_code', exam_code)
        set_session_data(session_id, 'exam_code_img', filepath)
        
        return jsonify({'exam_code': exam_code})
    except Exception as e:
        logger.error(f"Error scanning exam code: {e}")
        return jsonify({'error': 'Failed to process image'}), 500


@app.route('/exam/session/grade', methods=['POST'])
def grade_exam_answers():
    """Grade student answers against correct answers for the exam"""
    session_id = request.form.get('session_id')
    
    if not session_id or not get_session_data(session_id):
        return jsonify({'error': 'Invalid session'}), 400
    
    # Check if all required images are provided
    required = ['p1_img', 'p2_img', 'p3_img']
    if not all(k in request.files for k in required):
        return jsonify({'error': 'Missing answer sheet images'}), 400
    
    try:
        # Get session data
        data = get_session_data(session_id)
        exam_code = data.get('exam_code')
        
        if not exam_code:
            return jsonify({'error': 'No exam code found in session'}), 400
        
        # Save uploaded answer sheets
        files = {k: request.files[k] for k in required}
        filepaths = {}
        
        for key, file in files.items():
            filepath = save_uploaded_file(file, session_id, key)
            filepaths[key] = filepath
        
        # Scan student answers
        scanned_answers = scan_all_answers(
            filepaths['p1_img'],
            filepaths['p2_img'],
            filepaths['p3_img']
        )
        
        # Get correct answers for this exam
        correct_ans = get_cached_correct_answers(exam_code)
        
        if not correct_ans:
            return jsonify({
                'error': f'No correct answers found for exam code: {exam_code}'
            }), 404
        
        # Calculate score
        scores = score_answers(scanned_answers, correct_ans.answers)
        
        # Create exam record
        exam = Exam(
            exam_code=exam_code,
            score_p1=scores.get('p1_score', 0.0),
            score_p2=scores.get('p2_score', 0.0),
            score_p3=scores.get('p3_score', 0.0),
            total_score=scores.get('total_score', 0.0)
        )
        
        ExamDbService.create_exam(exam)
        
        # Cleanup session
        delete_session(session_id)
        
        scanned_count = (sum(len(v) for v in scanned_answers.values())
                         if isinstance(scanned_answers, dict)
                         else len(scanned_answers))
        
        return jsonify({
            'exam_code': exam_code,
            'p1_score': scores.get('p1_score', 0.0),
            'p2_score': scores.get('p2_score', 0.0),
            'p3_score': scores.get('p3_score', 0.0),
            'total_score': scores.get('total_score', 0.0),
            'scanned_answers_count': scanned_count,
            'message': 'Exam graded successfully'
        }), 201
    
    except Exception as e:
        logger.error(f"Error grading exam: {e}")
        return jsonify({'error': 'Failed to grade exam'}), 500


# ============================================================================
# EXAM CRUD ENDPOINTS
# ============================================================================

@app.route('/exams', methods=['GET'])
def list_exams():
    """List all exams with optional exam_code filter"""
    exam_code = request.args.get('exam_code')
    
    filter_dict = {}
    if exam_code:
        filter_dict['exam_code'] = exam_code
    
    exams = ExamDbService.list_exams(filter_dict)
    return jsonify(exams)


@app.route('/exams/<exam_id>', methods=['GET'])
def get_exam(exam_id):
    """Get specific exam by ID"""
    exam = ExamDbService.get_exam_by_id(exam_id)
    
    if not exam:
        return jsonify({'error': 'Exam not found'}), 404
    
    return jsonify(exam)


@app.route('/exams/<exam_id>', methods=['PUT'])
def update_exam(exam_id):
    """Update exam"""
    update_fields = request.get_json()
    
    if not update_fields:
        return jsonify({'error': 'No update data provided'}), 400
    
    success = ExamDbService.update_exam(exam_id, update_fields)
    
    if not success:
        return jsonify({'error': 'Exam not found or not updated'}), 404
    
    return jsonify({'message': 'Exam updated successfully'})


@app.route('/exams/<exam_id>', methods=['DELETE'])
def delete_exam(exam_id):
    """Delete exam"""
    success = ExamDbService.delete_exam(exam_id)
    
    if not success:
        return jsonify({'error': 'Exam not found'}), 404
    
    return jsonify({'message': 'Exam deleted successfully'})


@app.route('/exams', methods=['POST'])
def create_exam():
    """Create new exam (template or graded record)"""
    data = request.get_json()
    
    logger.info(f"Create exam data: {data}")
    
    # Check if this is creating correct answers (exam template)
    if 'answers' in data and 'exam_code' in data:
        return _create_exam_template(data)
    
    # Check if this is creating a graded exam record
    elif 'exam_code' in data and ('student_id' in data or
                                  'total_score' in data):
        return _create_graded_exam(data)
    
    else:
        return jsonify({
            'error': 'Invalid exam data. Provide answers+exam_code '
                     'for template, or exam_code+total_score for graded exam'
        }), 400


def _create_exam_template(data):
    """Create exam template with correct answers"""
    required = ['exam_code', 'answers']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing exam_code or answers'}), 400
    
    answers = data['answers']
    if not answers or not isinstance(answers, list):
        return jsonify({'error': 'Correct answers required'}), 400
    
    exam_code = data['exam_code']
    
    try:
        # Save correct answers first
        CorrectAnsDbService.update_correct_ans(exam_code, answers)
        
        # Create exam record (initially with 0 score)
        exam = Exam(
            exam_code=exam_code,
            total_score=0.0,
            created_by=data.get('created_by')
        )
        
        ExamDbService.create_exam(exam)
        
        # Get the created exam to return its ID
        # Since create_exam doesn't return ID, we need to find it
        exams = ExamDbService.list_exams({'exam_code': exam_code})
        if exams:
            exam_id = exams[0]['_id']
        else:
            exam_id = None
        
        return jsonify({
            'message': 'Exam template created with correct answers',
            'exam_code': exam_code,
            'answers_count': len(answers),
            'exam_id': exam_id
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating exam template: {e}")
        return jsonify({'error': 'Failed to create exam template'}), 500


def _create_graded_exam(data):
    """Create graded exam record"""
    required = ['exam_code']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing exam_code'}), 400
    
    exam_code = data['exam_code']
    
    try:
        # Create graded exam record
        exam = Exam(
            exam_code=exam_code,
            score_p1=data.get('score_p1', 0.0),
            score_p2=data.get('score_p2', 0.0),
            score_p3=data.get('score_p3', 0.0),
            total_score=data.get('total_score', 0.0),
            created_by=data.get('created_by')
        )
        
        ExamDbService.create_exam(exam)
        
        # Get the created exam to return its ID
        exams = ExamDbService.list_exams({'exam_code': exam_code})
        if exams:
            exam_id = exams[-1]['_id']  # Get the last one (most recent)
        else:
            exam_id = None
        
        return jsonify({
            'message': 'Graded exam record created',
            'exam_code': exam_code,
            'exam_id': exam_id,
            'total_score': exam.total_score
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating graded exam: {e}")
        return jsonify({'error': 'Failed to create graded exam'}), 500


# ============================================================================
# CORRECT ANSWERS CRUD ENDPOINTS
# ============================================================================

@app.route('/correctans', methods=['POST'])
def create_correct_answers():
    """Create correct answers from images"""
    if not all(k in request.files for k in ['p1_img', 'p2_img', 'p3_img']):
        return jsonify({'error': 'Missing image files'}), 400
    
    exam_code = request.form.get('exam_code')
    if not exam_code:
        return jsonify({'error': 'Missing exam_code'}), 400
    
    try:
        # Save uploaded files
        p1_file = request.files['p1_img']
        p2_file = request.files['p2_img']
        p3_file = request.files['p3_img']
        
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=secure_filename(p1_file.filename)
        ) as tmp1, \
            tempfile.NamedTemporaryFile(
                delete=False, suffix=secure_filename(p2_file.filename)
            ) as tmp2, \
            tempfile.NamedTemporaryFile(
                delete=False, suffix=secure_filename(p3_file.filename)
            ) as tmp3:
            
            p1_file.save(tmp1.name)
            p2_file.save(tmp2.name)
            p3_file.save(tmp3.name)
            
            # Scan answers
            answers = scan_all_answers(tmp1.name, tmp2.name, tmp3.name)
        
        # Save to database
        correct_ans = CorrectAns(id=exam_code, answers=answers)
        correctans_id = CorrectAnsDbService.create_correct_ans(correct_ans)
        
        return jsonify({
            'message': 'Correct answers created',
            'correctans_id': correctans_id,
            'exam_code': exam_code,
            'answers_count': len(answers)
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating correct answers: {e}")
        return jsonify({'error': 'Failed to create correct answers'}), 500


@app.route('/correctans/manual', methods=['POST'])
def create_correct_answers_manual():
    """Manually create correct answers"""
    try:
        data = request.get_json()
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        return jsonify({'error': 'Invalid JSON format'}), 400
    
    if data is None:
        logger.error("JSON data is None")
        return jsonify({'error': 'Invalid JSON'}), 400
    
    exam_code = data.get('exam_code')
    answers = data.get('answers')
    
    if not exam_code or not answers:
        return jsonify({'error': 'Invalid data'}), 400
    
    # Accept both old list format and new dict format
    if not isinstance(answers, (list, dict)):
        return jsonify({'error': 'Invalid answers format'}), 400
    
    try:
        CorrectAnsDbService.update_correct_ans(exam_code, answers)
        
        return jsonify({
            'message': 'Correct answers saved',
            'exam_code': exam_code,
            'answers_count': (len(answers) if isinstance(answers, list)
                              else sum(len(v) for v in answers.values()))
        }), 201
    
    except Exception as e:
        logger.error(f"Error saving correct answers: {e}")
        return jsonify({'error': 'Failed to save correct answers'}), 500


@app.route('/correctans/<exam_code>', methods=['GET'])
def get_correct_answers(exam_code):
    """Get correct answers by exam code"""
    correct_ans = CorrectAnsDbService.get_correct_ans_by_exam_code(exam_code)
    
    if not correct_ans:
        return jsonify({'error': 'Correct answers not found'}), 404
    
    return jsonify({
        'exam_code': correct_ans.id,
        'answers': correct_ans.answers,
        'answers_count': len(correct_ans.answers)
    })


@app.route('/correctans/<exam_code>', methods=['PUT'])
def update_correct_answers(exam_code):
    """Update correct answers"""
    data = request.get_json()
    answers = data.get('answers')
    
    if not isinstance(answers, list):
        return jsonify({'error': 'Invalid answers data'}), 400
    
    success = CorrectAnsDbService.update_correct_ans(exam_code, answers)
    
    if not success:
        return jsonify({'error': 'Failed to update'}), 500
    
    return jsonify({'message': 'Correct answers updated'})


@app.route('/correctans/<exam_code>', methods=['DELETE'])
def delete_correct_answers(exam_code):
    """Delete correct answers"""
    success = CorrectAnsDbService.delete_correct_ans(exam_code)
    
    if not success:
        return jsonify({'error': 'Correct answers not found'}), 404
    
    return jsonify({'message': 'Correct answers deleted'})


@app.route('/correctans', methods=['GET'])
def list_correct_answers():
    """List all correct answers"""
    correct_ans_list = CorrectAnsDbService.list_all_correct_ans()
    
    return jsonify([
        {
            'exam_code': ca.id,
            'answers_count': len(ca.answers)
        }
        for ca in correct_ans_list
    ])


# ============================================================================
# DIRECT SCAN ENDPOINTS (Single step)
# ============================================================================

@app.route('/scan/exam_code', methods=['POST'])
def scan_exam_code_direct():
    """Direct scan of exam code image"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        file = request.files['image']
        
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=secure_filename(file.filename)
        ) as tmp:
            file.save(tmp.name)
            result = scan_exam_code(tmp.name)
        
        return jsonify({'exam_code': result})
    
    except Exception as e:
        logger.error(f"Error scanning exam code: {e}")
        return jsonify({'error': 'Failed to scan'}), 500


@app.route('/scan/answers', methods=['POST'])
def scan_answers_direct():
    """Direct scan of all answer sheets"""
    required = ['p1_img', 'p2_img', 'p3_img']
    if not all(k in request.files for k in required):
        return jsonify({'error': 'Missing image files'}), 400
    
    try:
        files = {k: request.files[k] for k in required}
        
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=secure_filename(files['p1_img'].filename)
        ) as tmp1, \
             tempfile.NamedTemporaryFile(
                 delete=False, suffix=secure_filename(files['p2_img'].filename)
             ) as tmp2, \
             tempfile.NamedTemporaryFile(
                 delete=False, suffix=secure_filename(files['p3_img'].filename)
             ) as tmp3:
            
            files['p1_img'].save(tmp1.name)
            files['p2_img'].save(tmp2.name)
            files['p3_img'].save(tmp3.name)
            
            answers = scan_all_answers(tmp1.name, tmp2.name, tmp3.name)
        
        return jsonify({
            'answers': answers,
            'answers_count': (len(answers) if isinstance(answers, list)
                              else sum(len(v) for v in answers.values()))
        })
    
    except Exception as e:
        logger.error(f"Error scanning answers: {e}")
        return jsonify({'error': 'Failed to scan'}), 500


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """System health check"""
    try:
        from pymongo import MongoClient
        MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        client = MongoClient(MONGO_URI)
        db = client['be_db']
        db.command('ping')
        mongo_status = "healthy"
    except Exception:
        mongo_status = "unhealthy"
    
    redis_status = "not_configured"
    if USE_REDIS:
        try:
            redis_client.ping()
            redis_status = "healthy"
        except Exception:
            redis_status = "unhealthy"
    
    session_count = 0
    if USE_REDIS:
        session_count = len(redis_client.keys("session:*"))
    else:
        session_count = len(scan_sessions)
    
    return jsonify({
        'status': 'healthy' if mongo_status == 'healthy' else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'mongodb': mongo_status,
            'redis': redis_status
        },
        'metrics': {
            'active_sessions': session_count
        }
    })


@app.route('/', methods=['GET'])
def root():
    """API root endpoint"""
    return jsonify({
        'name': 'Exam Grading API',
        'version': '1.0.0',
        'endpoints': {
            'auth': '/auth/*',
            'exams': '/exams',
            'correctans': '/correctans',
            'sessions': '/exam/session/*',
            'scan': '/scan/*',
            'health': '/health'
        }
    })


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    logger.info("Starting Exam Grading API...")
    app.run(host='0.0.0.0', port=5000, debug=False)
