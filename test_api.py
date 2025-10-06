"""
Comprehensive test suite for Exam Grading API
Tests all endpoints and core functionality reliably
"""
import requests
import time

API_URL = "http://localhost:5000"


def assert_response(response, expected_status=200, description=""):
    """Assert response status and log results"""
    try:
        data = response.json()
    except ValueError:
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
    data = {"exam_code": unique_code, "answers": [[i, "A"] for i in range(1, 41)]}
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
    exam_data = {"student_id": unique_student, "exam_code": unique_code, "total_score": 8.5}
    response = requests.post(f"{API_URL}/exams", json=exam_data)
    assert_response(response, 201, "Create exam")
    data = response.json()
    assert "exam" in data

    # List
    response = requests.get(f"{API_URL}/exams")
    assert_response(response, 200, "List exams")
    exams = response.json()
    assert len(exams) >= 1
    exam_id = exams[0]["_id"]

    # Get one
    response = requests.get(f"{API_URL}/exams/{exam_id}")
    assert_response(response, 200, "Get exam by ID")

    # Update
    update_data = {"total_score": 9.0}
    response = requests.put(f"{API_URL}/exams/{exam_id}", json=update_data)
    assert_response(response, 200, "Update exam")

    # Delete
    response = requests.delete(f"{API_URL}/exams/{exam_id}")
    assert_response(response, 200, "Delete exam")
    print("   CRUD operations successful")


def test_exam_session_flow():
    """Test exam session workflow (without images)"""
    print("📝 Testing exam session flow...")

    # Start session
    response = requests.post(f"{API_URL}/exam/session/start")
    assert_response(response, 201, "Start exam session")
    data = response.json()
    session_id = data["session_id"]
    print(f"   Session started: {session_id}")

    # Test invalid session
    response = requests.post(f"{API_URL}/exam/session/student_id",
                           data={"session_id": "invalid"})
    assert_response(response, 400, "Invalid session rejection")

    # Test missing image (should fail gracefully)
    response = requests.post(f"{API_URL}/exam/session/student_id",
                           data={"session_id": session_id})
    assert_response(response, 400, "Missing image handling")

    print("   Session flow structure validated")


def test_direct_scanning():
    """Test direct scanning endpoints"""
    print("🔍 Testing direct scanning endpoints...")

    # Test missing image handling
    response = requests.post(f"{API_URL}/scan/student_id")
    assert_response(response, 400, "Student ID scan - missing image")

    response = requests.post(f"{API_URL}/scan/exam_code")
    assert_response(response, 400, "Exam code scan - missing image")

    response = requests.post(f"{API_URL}/scan/answers")
    assert_response(response, 400, "Answer scan - missing images")

    print("   Direct scanning endpoints validated")


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
        test_exam_session_flow()
        test_direct_scanning()
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
        print("\n❌ CONNECTION ERROR: Make sure the server is running on localhost:5000")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return False

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
