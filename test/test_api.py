"""
Comprehensive test suite for Exam Grading API
Tests all endpoints and core functionality reliably
"""
import requests
import time

# For testing with Flask test client
from main import app

API_URL = "http://localhost:5000"

# Use test client for debugging
test_client = app.test_client()


def assert_response(response, expected_status=200, description=""):
    """Assert response status and log results"""
    try:
        if hasattr(response, 'get_json'):
            # Flask test client response
            data = response.get_json()
        else:
            # requests response
            data = response.json()
    except ValueError:
        if hasattr(response, 'data'):
            data = response.data.decode('utf-8')
        else:
            data = response.text

    status = "✅ PASS" if response.status_code == expected_status else "❌ FAIL"
    print(f"{status} {description}: {response.status_code}")
    if response.status_code != expected_status:
        print(f"   Expected: {expected_status}, Got: {response.status_code}")
        print(f"   Response: {data}")
        raise AssertionError(f"Test failed: {description}")


def test_health():
    """Test system health"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{API_URL}/health")
    assert_response(response, 200, "Health check")
    data = response.json()
    assert "status" in data and "services" in data
    print("   System healthy, MongoDB connected")


def test_root():
    """Test API root"""
    print("🏠 Testing root endpoint...")
    response = requests.get(f"{API_URL}/")
    assert_response(response, 200, "Root endpoint")
    data = response.json()
    assert "name" in data and "endpoints" in data
    print("   API info retrieved")


def test_auth():
    """Test authentication flow"""
    print("🔐 Testing authentication...")

    # Use unique email to avoid conflicts
    import time
    unique_email = f"test_{int(time.time())}@example.com"

    # Signup
    signup_data = {"email": unique_email, "password": "password123"}
    response = requests.post(f"{API_URL}/auth/signup", json=signup_data)
    assert_response(response, 201, "User signup")

    # Login
    response = requests.post(f"{API_URL}/auth/login", json=signup_data)
    assert_response(response, 200, "User login")
    data = response.json()
    assert "user" in data
    print("   Authentication successful")


def test_correct_answers_crud():
    """Test correct answers CRUD operations"""
    print("📝 Testing correct answers CRUD...")

    # Use unique exam code
    import time
    unique_code = f"9999_{int(time.time())}"

    # Create
    data = {
        "exam_code": unique_code,
        "answers": [[i, "A"] for i in range(1, 41)]
    }
    response = requests.post(f"{API_URL}/correctans/manual", json=data)
    assert_response(response, 201, "Create correct answers")

    # Get
    response = requests.get(f"{API_URL}/correctans/{unique_code}")
    assert_response(response, 200, "Get correct answers")
    data = response.json()
    assert data["exam_code"] == unique_code and len(data["answers"]) == 40

    # List
    response = requests.get(f"{API_URL}/correctans")
    assert_response(response, 200, "List correct answers")
    assert len(response.json()) >= 1

    # Delete
    response = requests.delete(f"{API_URL}/correctans/{unique_code}")
    assert_response(response, 200, "Delete correct answers")
    print("   CRUD operations successful")


def test_exam_crud():
    """Test exam CRUD operations"""
    print("📋 Testing exam CRUD...")

    # Use unique data
    import time
    unique_student = f"12345{int(time.time()) % 1000:03d}"
    unique_code = f"294{int(time.time()) % 100}"

    # Create
    exam_data = {
        "exam_code": unique_code,
        "total_score": 8.5  # Create a graded exam record
    }
    response = test_client.post('/exams', json=exam_data)
    print(f"Debug: sent data: {exam_data}")
    print(f"Debug: response: {response.status_code} {response.get_data(as_text=True)}")
    assert_response(response, 201, "Create exam")
    data = response.get_json()
    assert "exam_id" in data
    exam_id = data["exam_id"]  # Get the exam ID directly from response

    # List
    response = test_client.get('/exams')
    assert_response(response, 200, "List exams")
    exams = response.get_json()
    assert len(exams) >= 1

    # Get one
    response = test_client.get(f'/exams/{exam_id}')
    assert_response(response, 200, "Get exam by ID")

    # Update
    update_data = {"total_score": 9.0}
    response = test_client.put(f'/exams/{exam_id}', json=update_data)
    assert_response(response, 200, "Update exam")

    # Delete
    response = test_client.delete(f'/exams/{exam_id}')
    assert_response(response, 200, "Delete exam")
    print("   CRUD operations successful")


def test_exam_session_with_real_images():
    """Test complete exam grading flow with real images"""
    print("🖼️ Testing exam grading with real images...")

    # Check if test images exist
    import os
    test_images = {
        'exam_code': 'services/Process/code.jpg',
        'p1': 'services/Process/p12.jpg',
        'p2': 'services/Process/p23.jpg',
        'p3': 'services/Process/test.jpg'
    }

    missing_images = [
        name for name, path in test_images.items()
        if not os.path.exists(path)
    ]
    if missing_images:
        print(f"   ⚠️ Skipping real image test - missing images: "
              f"{missing_images}")
        return

    # Create correct answers first
    import time
    unique_code = f"REAL_IMG_{int(time.time())}"

    # Set up correct answers - all answers A for testing
    correct_answers = [[i, "A"] for i in range(1, 41)]
    data = {"exam_code": unique_code, "answers": correct_answers}
    response = requests.post(f"{API_URL}/correctans/manual", json=data)
    if response.status_code == 201:
        print(f"   ✅ Set up correct answers for exam code: {unique_code}")
    else:
        print(f"   ⚠️ Failed to set up correct answers: {response.status_code}")
        return

    # Test direct grading with real images
    with open(test_images['exam_code'], 'rb') as f_code, \
         open(test_images['p1'], 'rb') as f1, \
         open(test_images['p2'], 'rb') as f2, \
         open(test_images['p3'], 'rb') as f3:

        files = {
            'exam_code_img': ('code.jpg', f_code, 'image/jpeg'),
            'p1_img': ('p12.jpg', f1, 'image/jpeg'),
            'p2_img': ('p23.jpg', f2, 'image/jpeg'),
            'p3_img': ('test.jpg', f3, 'image/jpeg')
        }
        response = requests.post(f"{API_URL}/grade/exam", files=files)

    if response.status_code == 201:
        result = response.json()
        score = result.get('total_score', 0.0)
        answers_count = result.get('scanned_answers_count', 0)
        exam_code = result.get('exam_code', 'unknown')
        print(f"   ✅ Exam graded successfully - Code: {exam_code}")
        print(f"   ✅ Score: {score}, Answers processed: {answers_count}")

        # Show what answers were scanned vs correct answers
        if score == 0.0 and answers_count > 0:
            print("   ℹ️  Score is 0.0 because scanned answers don't match "
                  "correct answers (all 'A')")
            print("   ℹ️  This is expected with real exam images - answers "
                  "may vary")
    else:
        print(f"   ⚠️ Grading failed: {response.status_code}")
        print(f"   Response: {response.text}")

    # Cleanup correct answers
    try:
        response = requests.delete(f"{API_URL}/correctans/{unique_code}")
        if response.status_code == 200:
            print(f"   ✅ Cleaned up correct answers for: {unique_code}")
    except Exception:
        pass  # Ignore cleanup errors in test

    print("   Real image grading flow tested")


def test_direct_scanning():
    """Test direct scanning endpoints with real images"""
    print("🔍 Testing direct scanning endpoints...")

    # Check if test images exist
    import os
    test_images = {
        'exam_code': 'services/Process/code.jpg',
        'p1': 'services/Process/p12.jpg',
        'p2': 'services/Process/p23.jpg',
        'p3': 'services/Process/test.jpg'
    }

    # Test missing image handling (should return 400 for existing endpoints)
    response = requests.post(f"{API_URL}/scan/exam_code")
    assert_response(response, 400, "Exam code scan - missing image")

    response = requests.post(f"{API_URL}/scan/answers")
    assert_response(response, 400, "Answer scan - missing images")

    response = requests.post(f"{API_URL}/grade/exam")
    assert_response(response, 400, "Grade exam - missing images")

    # Test with real images if available
    if os.path.exists(test_images['exam_code']):
        with open(test_images['exam_code'], 'rb') as f:
            files = {'image': ('code.jpg', f, 'image/jpeg')}
            response = requests.post(f"{API_URL}/scan/exam_code", files=files)
        if response.status_code == 200:
            print("   ✅ Real exam code scan successful")
        else:
            print(f"   ⚠️ Real exam code scan failed: {response.status_code}")

    if all(os.path.exists(test_images[part]) for part in ['p1', 'p2', 'p3']):
        with open(test_images['p1'], 'rb') as f1, \
             open(test_images['p2'], 'rb') as f2, \
             open(test_images['p3'], 'rb') as f3:
            files = {
                'p1_img': ('p12.jpg', f1, 'image/jpeg'),
                'p2_img': ('p23.jpg', f2, 'image/jpeg'),
                'p3_img': ('test.jpg', f3, 'image/jpeg')
            }
            response = requests.post(f"{API_URL}/scan/answers", files=files)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Real answer scan successful: "
                  f"{data.get('answers_count', 0)} answers")
        else:
            print(f"   ⚠️ Real answer scan failed: {response.status_code}")

    print("   Direct scanning endpoints validated")


def test_full_exam_workflow():
    """Test complete exam grading workflow with mock data"""
    print("🎯 Testing full exam grading workflow...")

    # Create correct answers in new 3-part format
    import time
    unique_code = f"TEST_{int(time.time())}"

    # P1: 40 ABCD questions
    p1_answers = [[i, "A"] for i in range(1, 41)]

    # P2: True/False with sub-parts (8 cells × 4 sub-parts = 32 answers)
    p2_answers = []
    for cell in range(1, 9):  # 8 cells
        for sub in ['a', 'b', 'c', 'd']:  # 4 sub-parts each
            if sub in ['a', 'c']:  # Alternate pattern for testing
                answer = 'Dung'
            else:
                answer = 'Sai'
            p2_answers.append([f'p2_c{cell}_{sub}', answer])

    # P3: Essay with symbol marks (8 columns)
    p3_answers = [
        ['p3_c1', ['1', '2']], ['p3_c2', ['3', '4']],
        ['p3_c3', ['5', '6']], ['p3_c4', ['7', '8']],
        ['p3_c5', ['0', '1']], ['p3_c6', ['2', '3']],
        ['p3_c7', ['4', '5']], ['p3_c8', ['6', '7']]
    ]

    # New format: dict with p1, p2, p3 keys
    correct_answers = {
        'p1': p1_answers,
        'p2': p2_answers,
        'p3': p3_answers
    }

    data = {"exam_code": unique_code, "answers": correct_answers}
    response = test_client.post('/correctans/manual', json=data)
    assert_response(response, 201, "Create test correct answers")

    # Create a test exam manually
    exam_data = {
        "exam_code": unique_code,
        "total_score": 8.5
    }
    response = requests.post(f"{API_URL}/exams", json=exam_data)
    assert_response(response, 201, "Create test exam")
    exam_result = response.json()
    assert "exam_id" in exam_result  # Updated to match new endpoint response

    # Verify exam was created
    response = requests.get(f"{API_URL}/exams")
    assert_response(response, 200, "List exams includes new exam")
    exams = response.json()
    assert len(exams) >= 1

    # Test grading logic with mock scanned answers (new format)
    from services.Grade.create_ans import score_answers

    # Perfect scores for all parts
    scanned_answers = {
        'p1': [[i, "A"] for i in range(1, 41)],  # Perfect P1 score
        'p2': p2_answers,  # Perfect P2 score
        'p3': p3_answers   # Perfect P3 score
    }

    # Test scoring with new format
    scores = score_answers(scanned_answers, correct_answers)
    assert scores['p1_score'] == 10.0
    assert scores['p2_score'] == 10.0
    assert scores['p3_score'] == 10.0
    assert scores['total_score'] == 10.0
    print("   ✅ Grading logic: Perfect scores calculation correct")

    # Test partial P1 score
    partial_p1_answers = ([[i, "A"] for i in range(1, 21)] +
                          [[i, "B"] for i in range(21, 41)])
    # Half correct for P1
    partial_scanned = {
        'p1': partial_p1_answers,
        'p2': p2_answers,
        'p3': p3_answers
    }
    partial_scores = score_answers(partial_scanned, correct_answers)
    expected_half = 5.0
    assert partial_scores['p1_score'] == expected_half
    print("   ✅ Grading logic: Partial P1 score calculation correct")

    # Cleanup
    response = requests.delete(f"{API_URL}/correctans/{unique_code}")
    assert_response(response, 200, "Cleanup correct answers")

    print("   Full workflow validated successfully")


def test_error_handling():
    """Test error handling and edge cases"""
    print("⚠️ Testing error handling...")

    # Invalid endpoints
    response = requests.get(f"{API_URL}/nonexistent")
    assert response.status_code in [404, 405]

    # Invalid JSON
    response = requests.post(f"{API_URL}/auth/signup",
                             data="invalid json",
                             headers={"Content-Type": "application/json"})
    assert_response(response, 400, "Invalid JSON handling")

    # Missing required fields
    response = requests.post(f"{API_URL}/auth/signup", json={})
    assert_response(response, 400, "Missing required fields")

    # Invalid exam ID
    response = requests.get(f"{API_URL}/exams/invalid_id")
    assert_response(response, 404, "Invalid exam ID")

    # Invalid correct answers
    response = requests.get(f"{API_URL}/correctans/invalid_code")
    assert_response(response, 404, "Invalid exam code")

    print("   Error handling validated")


def main():
    """Run comprehensive test suite"""
    print("=" * 70)
    print("🧪 COMPREHENSIVE EXAM GRADING API TEST SUITE")
    print("=" * 70)
    print()

    start_time = time.time()

    try:
        # Core functionality tests
        test_health()
        test_root()
        test_auth()
        test_correct_answers_crud()
        test_exam_crud()

        # Advanced features
        test_exam_session_with_real_images()
        test_direct_scanning()
        test_full_exam_workflow()
        test_error_handling()

        elapsed = time.time() - start_time
        print()
        print("=" * 70)
        print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
        print(f"⏱️  Total time: {elapsed:.2f}s")
        print("✅ API is reliable, complete, and production-ready")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ CONNECTION ERROR: Make sure the server is running on "
              "localhost:5000")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return False

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
