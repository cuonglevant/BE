
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import tempfile
from werkzeug.utils import secure_filename
import redis
import logging
import time
import atexit
import shutil
import os
from datetime import datetime, timedelta
from functools import lru_cache

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client (fallback to in-memory if Redis not available)
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
    USE_REDIS = True
    logger.info("Redis connected successfully")
except:
    redis_client = None
    USE_REDIS = False
    logger.warning("Redis not available, using in-memory session storage")

from services.Grade.create_ans import score_answers, scan_all_answers
from Models.correctans import CorrectAns

# Error messages constants
INVALID_SESSION_MSG = 'Invalid session_id'
NO_IMAGE_MSG = 'No image uploaded'

# Helper functions
def get_session_temp_dir(session_id):
    """Create and return temp directory for session"""
    temp_dir = os.path.join(tempfile.gettempdir(), f"exam_session_{session_id}")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def cleanup_temp_files():
    """Cleanup all temp session directories"""
    temp_root = tempfile.gettempdir()
    for dir_name in os.listdir(temp_root):
        if dir_name.startswith("exam_session_"):
            shutil.rmtree(os.path.join(temp_root, dir_name), ignore_errors=True)
            logger.info(f"Cleaned up temp directory: {dir_name}")

# Register cleanup on exit
atexit.register(cleanup_temp_files)

def initialize_db_indexes():
	"""Create MongoDB indexes for better performance"""
	try:
		from pymongo import MongoClient
		import os
		MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
		client = MongoClient(MONGO_URI)
		db = client['be_db']
		
		# Create indexes
		correctans_collection = db['correctans']
		correctans_collection.create_index("id")  # For exam_code lookup
		
		exams_collection = db['exams']
		exams_collection.create_index([("student_id", 1), ("exam_code", 1)])
		exams_collection.create_index("created_at")
		exams_collection.create_index("created_by")
		
		logger.info("MongoDB indexes created successfully")
	except Exception as e:
		logger.error(f"Error creating indexes: {e}")

def validate_scan_result(scan_type, result):
    """Validate scan results"""
    if scan_type == 'student_id':
        # SBD must be 8 digits
        return result and len(result) == 8 and result.isdigit()
    elif scan_type == 'exam_code':
        # Exam code must be 4 digits
        return result and len(result) == 4 and result.isdigit()
    elif scan_type in ['p1', 'p2', 'p3']:
        # Score must be 0-10
        try:
            score = float(result)
            return 0 <= score <= 10
        except:
            return False
    return False

@lru_cache(maxsize=100)
def get_correct_answers_by_exam_code_cached(exam_code):
    """Cache correct answers by exam_code to reduce DB queries"""
    try:
        from pymongo import MongoClient
        import os
        MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        client = MongoClient(MONGO_URI)
        db = client['be_db']
        correctans_collection = db['correctans']
        correct_data = correctans_collection.find_one({'id': str(exam_code)})
        if correct_data:
            return CorrectAns(correct_data['id'], correct_data['answers'])
    except Exception as e:
        logger.error(f"Error fetching correct answers: {e}")
    return None

# Session management functions
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
        redis_client.hset(f"session:{session_id}", key, value)
        redis_client.expire(f"session:{session_id}", timedelta(minutes=30))
    else:
        if session_id not in scan_sessions:
            scan_sessions[session_id] = {}
        scan_sessions[session_id][key] = value

def delete_session(session_id):
    """Delete session from Redis or memory"""
    if USE_REDIS:
        redis_client.delete(f"session:{session_id}")
    else:
        scan_sessions.pop(session_id, None)
    
    # Cleanup temp directory
    temp_dir = get_session_temp_dir(session_id)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

# Request logging middleware
@app.before_request
def before_request():
    g.start_time = time.time()
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        logger.info(f"Response: {response.status} - {elapsed:.3f}s")
    return response

# Endpoint chấm điểm đáp án
@app.route('/exam/score', methods=['POST'])
def score_exam():
	data = request.get_json()
	scanned_ans = data.get('scanned_ans')  # [(câu, đáp án), ...]
	correct_ans = data.get('correct_ans')  # [(câu, đáp án), ...]
	if not scanned_ans or not correct_ans:
		return jsonify({'error': 'Missing answers'}), 400
	score = score_answers(scanned_ans, correct_ans)
	return jsonify({'score': score})
import uuid

# Lưu tạm dữ liệu từng session
scan_sessions = {}

@app.route('/exam/start', methods=['POST'])
def start_exam_session():
	session_id = str(uuid.uuid4())
	if USE_REDIS:
		# Store in Redis with TTL
		redis_client.hset(f"session:{session_id}", mapping={
			"created_at": datetime.now().isoformat(),
			"status": "started"
		})
		redis_client.expire(f"session:{session_id}", timedelta(minutes=30))
	else:
		# Fallback to memory
		scan_sessions[session_id] = {
			"created_at": datetime.now().isoformat(),
			"status": "started"
		}
	logger.info(f"Started exam session: {session_id}")
	return jsonify({'session_id': session_id})

@app.route('/exam/student_id', methods=['POST'])
def receive_student_id():
	session_id = request.form.get('session_id')
	session_data = get_session_data(session_id)
	if not session_id or not session_data:
		return jsonify({'error': INVALID_SESSION_MSG}), 400
	file = request.files.get('image')
	if not file:
		return jsonify({'error': NO_IMAGE_MSG}), 400
	
	try:
		filename = secure_filename(file.filename)
		temp_dir = get_session_temp_dir(session_id)
		temp_path = os.path.join(temp_dir, f"student_id_{filename}")
		file.save(temp_path)
		
		student_id = scan_student_id(temp_path)
		
		# Validate result
		if not validate_scan_result('student_id', student_id):
			logger.warning(f"Invalid student_id scan result: {student_id}")
			return jsonify({'error': f'Invalid student ID format: {student_id}'}), 400
		
		set_session_data(session_id, 'student_id', student_id)
		logger.info(f"Session {session_id}: scanned student_id = {student_id}")
		return jsonify({'student_id': student_id})
	except Exception as e:
		logger.error(f"Error processing student_id: {e}")
		return jsonify({'error': 'Failed to process image'}), 500

@app.route('/exam/exam_code', methods=['POST'])
def receive_exam_code():
	session_id = request.form.get('session_id')
	session_data = get_session_data(session_id)
	if not session_id or not session_data:
		return jsonify({'error': INVALID_SESSION_MSG}), 400
	file = request.files.get('image')
	if not file:
		return jsonify({'error': NO_IMAGE_MSG}), 400
	
	try:
		filename = secure_filename(file.filename)
		temp_dir = get_session_temp_dir(session_id)
		temp_path = os.path.join(temp_dir, f"exam_code_{filename}")
		file.save(temp_path)
		
		exam_code = scan_exam_code(temp_path)
		
		# Validate result
		if not validate_scan_result('exam_code', exam_code):
			logger.warning(f"Invalid exam_code scan result: {exam_code}")
			return jsonify({'error': f'Invalid exam code format: {exam_code}'}), 400
		
		set_session_data(session_id, 'exam_code', exam_code)
		logger.info(f"Session {session_id}: scanned exam_code = {exam_code}")
		return jsonify({'exam_code': exam_code})
	except Exception as e:
		logger.error(f"Error processing exam_code: {e}")
		return jsonify({'error': 'Failed to process image'}), 500

def process_part_scan(part_name, scan_func):
	"""Generic handler for p1, p2, p3 endpoints (session flow).

	Saves the uploaded image path into the session and returns an
	acknowledgement value so the client can proceed. Actual scoring is
	computed at /exam/finish using scan_all_answers.
	"""
	session_id = request.form.get('session_id')
	session_data = get_session_data(session_id)
	if not session_id or not session_data:
		return jsonify({'error': INVALID_SESSION_MSG}), 400
	file = request.files.get('image')
	if not file:
		return jsonify({'error': NO_IMAGE_MSG}), 400
	
	try:
		filename = secure_filename(file.filename)
		temp_dir = get_session_temp_dir(session_id)
		temp_path = os.path.join(temp_dir, f"{part_name}_{filename}")
		file.save(temp_path)
		
		# Save image path for finish step
		set_session_data(session_id, f'{part_name}_img', temp_path)
		
		# Optional early scan to warm up pipelines (ignore value/errors)
		try:
			_ = scan_func(temp_path)
		except Exception as scan_err:
			logger.warning(f"{part_name} early scan failed (ignored, will scan at finish): {scan_err}")
		
		# Do not treat p1/p2/p3 result here as a score. Use placeholder.
		placeholder_score = 0
		set_session_data(session_id, f'score_{part_name}', str(placeholder_score))
		logger.info(f"Session {session_id}: received image for {part_name}, placeholder score set to 0")
		return jsonify({f'score_{part_name}': placeholder_score})
	except Exception as e:
		logger.error(f"Error processing {part_name}: {e}")
		return jsonify({'error': f'Failed to process {part_name} image'}), 500

@app.route('/exam/p1', methods=['POST'])
def receive_p1():
	return process_part_scan('p1', scan_p1)

@app.route('/exam/p2', methods=['POST'])
def receive_p2():
	return process_part_scan('p2', scan_p2)

@app.route('/exam/p3', methods=['POST'])
def receive_p3():
	return process_part_scan('p3', scan_p3)

@app.route('/exam/finish', methods=['POST'])
def finish_exam():
	session_id = request.form.get('session_id')
	created_by = request.form.get('created_by')
	correct_ans_id = request.form.get('correct_ans_id')  # optional, not required
	
	session_data = get_session_data(session_id)
	if not session_id or not session_data:
		return jsonify({'error': INVALID_SESSION_MSG}), 400
	
	try:
		# Get all data from session
		data = {}
		if USE_REDIS:
			data = redis_client.hgetall(f"session:{session_id}")
		else:
			data = scan_sessions.get(session_id, {})
		
		# Check required fields (relaxed)
		required_fields = ['student_id', 'exam_code']
		if not all(field in data for field in required_fields):
			missing = [f for f in required_fields if f not in data]
			return jsonify({'error': f'Missing required data: {missing}'}), 400
		
		# Get scores with defaults
		score_p1 = float(data.get('score_p1', 0))
		score_p2 = float(data.get('score_p2', 0))
		score_p3 = float(data.get('score_p3', 0))
		
		# Scan answers if images available
		scanned_ans = []
		p1_img = data.get('p1_img')
		p2_img = data.get('p2_img')
		p3_img = data.get('p3_img')
		
		if p1_img and p2_img and p3_img:
			try:
				scanned_ans = scan_all_answers(p1_img, p2_img, p3_img)
				logger.info(f"Session {session_id}: scanned {len(scanned_ans)} answers")
			except Exception as e:
				logger.error(f"Error scanning answers: {e}")
		
		# Get correct answers with caching by exam_code (prefer session exam_code)
		correct_ans_obj = None
		if 'exam_code' in data:
			correct_ans_obj = get_correct_answers_by_exam_code_cached(data['exam_code'])
			if correct_ans_obj:
				logger.info(f"Using cached correct answers for exam_code={data['exam_code']}")
		
		# Calculate total score
		total_score = 0.0
		if correct_ans_obj and scanned_ans:
			total_score = score_answers(scanned_ans, correct_ans_obj.answers)
			logger.info(f"Session {session_id}: calculated total_score = {total_score}")
		
		# Create exam record
		exam = Exam(
			student_id=data['student_id'],
			exam_code=data['exam_code'],
			score_p1=score_p1,
			score_p2=score_p2,
			score_p3=score_p3,
			total_score=total_score,
			created_by=created_by if created_by else None,
			correct_ans=correct_ans_id if correct_ans_id else None
		)
		ExamDbService.create_exam(exam)
		logger.info(f"Session {session_id}: created exam record")
		
		# Cleanup session
		delete_session(session_id)
		
		return jsonify({
			'student_id': exam.student_id,
			'exam_code': exam.exam_code,
			'score_p1': exam.score_p1,
			'score_p2': exam.score_p2,
			'score_p3': exam.score_p3,
			'total_score': exam.total_score,
			'scanned_ans': scanned_ans,
			'correct_ans_id': str(exam.correct_ans) if exam.correct_ans else None
		})
	except Exception as e:
		logger.error(f"Error finishing exam: {e}")
		return jsonify({'error': 'Failed to complete exam processing'}), 500


from services.Auth.auth_service import AuthService
import os
from services.Db.exam_db_service import ExamDbService
from Models.exam import Exam

# Auth endpoints
@app.route('/signup', methods=['POST'])
def signup():
	data = request.get_json()
	email = data.get('email')
	password = data.get('password')
	result = AuthService.sign_up(email, password)
	return jsonify(result)

@app.route('/login', methods=['POST'])
def login():
	data = request.get_json()
	email = data.get('email')
	password = data.get('password')
	result = AuthService.login(email, password)
	return jsonify(result)

@app.route('/logout', methods=['POST'])
def logout():
	data = request.get_json()
	email = data.get('email')
	result = AuthService.logout(email)
	return jsonify(result)

# # Process endpoints

from services.Grade.scan_student_id import scan_exam_code, scan_p1, scan_p2, scan_p3

# Nhận ảnh trực tiếp cho từng phần
@app.route('/scan/student_id', methods=['POST'])
def scan_student_id_endpoint():
	if 'image' not in request.files:
		return jsonify({'error': 'No image uploaded'}), 400
	file = request.files['image']
	filename = secure_filename(file.filename)
	with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
		file.save(tmp.name)
		result = scan_student_id(tmp.name)
	return jsonify({'student_id': result})

@app.route('/scan/exam_code', methods=['POST'])
def scan_exam_code_endpoint():
	if 'image' not in request.files:
		return jsonify({'error': 'No image uploaded'}), 400
	file = request.files['image']
	filename = secure_filename(file.filename)
	with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
		file.save(tmp.name)
		result = scan_exam_code(tmp.name)
	return jsonify({'exam_code': result})

@app.route('/scan/p1', methods=['POST'])
def scan_p1_endpoint():
	if 'image' not in request.files:
		return jsonify({'error': 'No image uploaded'}), 400
	file = request.files['image']
	filename = secure_filename(file.filename)
	with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
		file.save(tmp.name)
		result = scan_p1(tmp.name)
	return jsonify({'score_p1': result})

@app.route('/scan/p2', methods=['POST'])
def scan_p2_endpoint():
	if 'image' not in request.files:
		return jsonify({'error': 'No image uploaded'}), 400
	file = request.files['image']
	filename = secure_filename(file.filename)
	with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
		file.save(tmp.name)
		result = scan_p2(tmp.name)
	return jsonify({'score_p2': result})

@app.route('/scan/p3', methods=['POST'])
def scan_p3_endpoint():
	if 'image' not in request.files:
		return jsonify({'error': 'No image uploaded'}), 400
	file = request.files['image']
	filename = secure_filename(file.filename)
	with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
		file.save(tmp.name)
		result = scan_p3(tmp.name)
	return jsonify({'score_p3': result})

# Exam CRUD endpoints
@app.route('/exam', methods=['POST'])
def create_exam():
	data = request.get_json()
	exam = Exam(
		student_id=data.get('student_id'),
		exam_code=data.get('exam_code'),
		score_p1=data.get('score_p1', 0.0),
		score_p2=data.get('score_p2', 0.0),
		score_p3=data.get('score_p3', 0.0),
		total_score=data.get('total_score', 0.0),
		created_by=data.get('created_by')
	)
	ExamDbService.create_exam(exam)
	return jsonify({'message': 'Exam created', 'exam': exam.to_dict()})

@app.route('/exam/<exam_id>', methods=['GET'])
def get_exam(exam_id):
	exam = ExamDbService.get_exam_by_id(exam_id)
	if exam:
		return jsonify(exam)
	return jsonify({'error': 'Exam not found'}), 404

@app.route('/exam/<exam_id>', methods=['PUT'])
def update_exam(exam_id):
	update_fields = request.get_json()
	success = ExamDbService.update_exam(exam_id, update_fields)
	if success:
		return jsonify({'message': 'Exam updated'})
	return jsonify({'error': 'Exam not found or not updated'}), 404

@app.route('/exam/<exam_id>', methods=['DELETE'])
def delete_exam(exam_id):
	success = ExamDbService.delete_exam(exam_id)
	if success:
		return jsonify({'message': 'Exam deleted'})
	return jsonify({'error': 'Exam not found'}), 404

@app.route('/exams', methods=['GET'])
def list_exams():
	exams = ExamDbService.list_exams()
	return jsonify(exams)

# Endpoint tạo đáp án đúng
@app.route('/correctans/create', methods=['POST'])
def create_correct_ans():
	p1_img = request.files.get('p1_img')
	p2_img = request.files.get('p2_img')
	p3_img = request.files.get('p3_img')
	exam_code = request.form.get('exam_code')

	if not p1_img or not p2_img or not p3_img or not exam_code:
		return jsonify({'error': 'Missing data'}), 400

	import tempfile
	from werkzeug.utils import secure_filename
	with tempfile.NamedTemporaryFile(delete=False, suffix=secure_filename(p1_img.filename)) as tmp1, \
		 tempfile.NamedTemporaryFile(delete=False, suffix=secure_filename(p2_img.filename)) as tmp2, \
		 tempfile.NamedTemporaryFile(delete=False, suffix=secure_filename(p3_img.filename)) as tmp3:
		p1_img.save(tmp1.name)
		p2_img.save(tmp2.name)
		p3_img.save(tmp3.name)
		answers = scan_all_answers(tmp1.name, tmp2.name, tmp3.name)

	from pymongo import MongoClient
	import os
	MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
	client = MongoClient(MONGO_URI)
	db = client['be_db']
	correctans_collection = db['correctans']
	result = correctans_collection.insert_one({'id': exam_code, 'answers': answers})

	return jsonify({'message': 'Correct answers created', 'answers': answers, 'correct_ans_id': str(result.inserted_id)})

# Search correct answers by exam_code
@app.route('/correctans/search', methods=['GET'])
def search_correct_ans():
	exam_code = request.args.get('exam_code')
	if not exam_code:
		return jsonify({'error': 'Missing exam_code'}), 400
	try:
		from pymongo import MongoClient
		import os
		MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
		client = MongoClient(MONGO_URI)
		db = client['be_db']
		correctans_collection = db['correctans']
		correct_data = correctans_collection.find_one({'id': exam_code})
		if not correct_data:
			return jsonify({'error': 'Not found'}), 404
		return jsonify({
			'correct_ans_id': str(correct_data.get('_id')),
			'exam_code': correct_data.get('id'),
			'answers': correct_data.get('answers', [])
		})
	except Exception as e:
		logger.error(f"Error searching correct answers: {e}")
		return jsonify({'error': 'Database error'}), 500

# Create correct answers manually from provided answers list
@app.route('/correctans/create_manual', methods=['POST'])
def create_correct_ans_manual():
	try:
		data = request.get_json(force=True, silent=True) or {}
		exam_code = data.get('exam_code')
		answers = data.get('answers')  # expected list of [question, answer]
		if not exam_code or not isinstance(answers, list):
			return jsonify({'error': 'Missing exam_code or answers'}), 400
		from pymongo import MongoClient
		import os
		MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
		client = MongoClient(MONGO_URI)
		db = client['be_db']
		correctans_collection = db['correctans']
		# upsert by exam_code id
		correctans_collection.update_one(
			{'id': exam_code},
			{'$set': {'answers': answers}},
			upsert=True
		)
		# fetch the document to get _id (for both insert/update)
		doc = correctans_collection.find_one({'id': exam_code})
		return jsonify({'message': 'Correct answers saved', 'correct_ans_id': str(doc.get('_id')), 'exam_code': exam_code, 'answers': answers})
	except Exception as e:
		logger.error(f"Error creating manual correct answers: {e}")
		return jsonify({'error': 'Failed to save correct answers'}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
	"""Check system health status"""
	try:
		# Check MongoDB
		from pymongo import MongoClient
		import os
		MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
		client = MongoClient(MONGO_URI)
		db = client['be_db']
		db.command('ping')
		mongo_status = "healthy"
	except:
		mongo_status = "unhealthy"
	
	# Check Redis
	redis_status = "healthy" if USE_REDIS and redis_client.ping() else "not_configured"
	
	# Get session count
	session_count = 0
	if USE_REDIS:
		session_count = len(redis_client.keys("session:*"))
	else:
		session_count = len(scan_sessions)
	
	return jsonify({
		'status': 'healthy' if mongo_status == 'healthy' else 'degraded',
		'services': {
			'mongodb': mongo_status,
			'redis': redis_status
		},
		'metrics': {
			'active_sessions': session_count
		},
		'timestamp': datetime.now().isoformat()
	})

if __name__ == '__main__':
    # Initialize DB indexes on startup
    initialize_db_indexes()
    
    # Run app
    app.run(host='0.0.0.0', port=5000)
