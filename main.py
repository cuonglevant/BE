"""
Backend API for Exam Grading System
Handles exam scanning, grading, and CRUD operations
"""
import os
import tempfile
import logging
import time
from datetime import datetime
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
from services.Grade.create_ans import scan_all_answers, score_answers
from services.Grade.scan_student_id import scan_exam_code

# Redis setup (optional)
USE_REDIS = False
redis_client = None

try:
    import redis
    redis_client = redis.Redis(
        host='localhost', port=6379, decode_responses=True
    )
    redis_client.ping()
    USE_REDIS = True
    logger.info("Redis connected successfully")
except ImportError:
    logger.warning("Redis library not available, using in-memory storage")
    USE_REDIS = False
except Exception as e:
    logger.warning(f"Redis not available ({e}), using in-memory storage")
    USE_REDIS = False


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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
    elif 'exam_code' in data and 'total_score' in data:
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

@app.route('/grade/exam', methods=['POST'])
def grade_exam_direct():
    """Grade exam directly from uploaded images"""
    required_files = ['exam_code_img', 'p1_img', 'p2_img', 'p3_img']
    if not all(k in request.files for k in required_files):
        return jsonify({'error': 'Missing required images: exam_code_img, p1_img, p2_img, p3_img'}), 400
    
    try:
        # Save uploaded files temporarily
        files = {k: request.files[k] for k in required_files}
        
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=secure_filename(files['exam_code_img'].filename)
        ) as tmp_exam_code, \
             tempfile.NamedTemporaryFile(
                 delete=False, suffix=secure_filename(files['p1_img'].filename)
             ) as tmp1, \
             tempfile.NamedTemporaryFile(
                 delete=False, suffix=secure_filename(files['p2_img'].filename)
             ) as tmp2, \
             tempfile.NamedTemporaryFile(
                 delete=False, suffix=secure_filename(files['p3_img'].filename)
             ) as tmp3:
            
            files['exam_code_img'].save(tmp_exam_code.name)
            files['p1_img'].save(tmp1.name)
            files['p2_img'].save(tmp2.name)
            files['p3_img'].save(tmp3.name)
            
            # Try to scan exam code, but allow override via form parameter or query parameter
            scanned_exam_code = scan_exam_code(tmp_exam_code.name)
            exam_code = (request.form.get('exam_code') or 
                        request.args.get('exam_code') or 
                        scanned_exam_code)
            
            logger.info(f"Scanned exam code: '{scanned_exam_code}', Form exam_code: '{request.form.get('exam_code')}', Query exam_code: '{request.args.get('exam_code')}', Final exam_code: '{exam_code}'")
            
            # If still no exam code, use a default for testing
            if not exam_code:
                exam_code = "DEFAULT_TEST"
                logger.warning(f"No exam code detected from image, using default: {exam_code}")
            
            # Scan student answers
            scanned_answers = scan_all_answers(tmp1.name, tmp2.name, tmp3.name)
            
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
            
            scanned_count = (sum(len(v) for v in scanned_answers.values())
                             if isinstance(scanned_answers, dict)
                             else len(scanned_answers))
            
            return jsonify({
                'exam_code': exam_code,
                'scanned_exam_code': scanned_exam_code,  # Include what was actually scanned
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
    
    return jsonify({
        'status': 'healthy' if mongo_status == 'healthy' else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'mongodb': mongo_status,
            'redis': redis_status
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
            'grade': '/grade/*',
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
