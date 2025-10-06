# Exam Grading System API

A complete backend system for scanning and grading multiple-choice exams with automatic scoring.

## 🚀 Features

- **Image Processing**: Scan student IDs, exam codes, and answer sheets using OpenCV
- **Automatic Grading**: Compare scanned answers against correct answer keys
- **Session Management**: Multi-step exam processing with temporary storage
- **CRUD Operations**: Full management of exams and correct answers
- **Authentication**: User signup/login/logout
- **Redis Support**: Optional Redis for session storage (falls back to in-memory)
- **Health Monitoring**: System health checks and metrics

## 📋 Requirements

```
Python 3.10+
MongoDB
Redis (optional)
```

## 🔧 Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd BE
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Create a `.env` file:
```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
COOKIE_SECRET=your-secret-key
JWT_SECRET=your-jwt-secret
```

4. **Run the application**
```bash
python main.py
```

The API will be available at `http://localhost:5000`

## 📚 API Endpoints

### 🔐 Authentication

#### Sign Up
```http
POST /auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

#### Logout
```http
POST /auth/logout
Content-Type: application/json

{
  "email": "user@example.com"
}
```

---

### 📝 Exam Session Flow (Multi-step)

Use this workflow when processing exams step-by-step:

#### 1. Start Session
```http
POST /exam/session/start

Response:
{
  "session_id": "uuid-string"
}
```

#### 2. Upload Student ID Image
```http
POST /exam/session/student_id
Content-Type: multipart/form-data

session_id: <session_id>
image: <file>

Response:
{
  "student_id": "12345678"
}
```

#### 3. Upload Exam Code Image
```http
POST /exam/session/exam_code
Content-Type: multipart/form-data

session_id: <session_id>
image: <file>

Response:
{
  "exam_code": "2942"
}
```

#### 4. Upload Answer Sheet Parts
```http
POST /exam/session/part/p1
POST /exam/session/part/p2
POST /exam/session/part/p3
Content-Type: multipart/form-data

session_id: <session_id>
image: <file>

Response:
{
  "message": "p1 uploaded successfully"
}
```

#### 5. Finish and Grade
```http
POST /exam/session/finish
Content-Type: multipart/form-data

session_id: <session_id>
created_by: <user_id> (optional)

Response:
{
  "student_id": "12345678",
  "exam_code": "2942",
  "total_score": 8.5,
  "scanned_answers_count": 40,
  "message": "Exam graded successfully"
}
```

---

### 📄 Exam CRUD Operations

#### List All Exams
```http
GET /exams
GET /exams?student_id=12345678
GET /exams?exam_code=2942

Response:
[
  {
    "_id": "...",
    "student_id": "12345678",
    "exam_code": "2942",
    "total_score": 8.5,
    "created_at": "2025-10-06T10:00:00"
  }
]
```

#### Get Specific Exam
```http
GET /exams/<exam_id>

Response:
{
  "_id": "...",
  "student_id": "12345678",
  "exam_code": "2942",
  "score_p1": 0.0,
  "score_p2": 0.0,
  "score_p3": 0.0,
  "total_score": 8.5,
  "created_at": "2025-10-06T10:00:00"
}
```

#### Create Exam Manually
```http
POST /exams
Content-Type: application/json

{
  "student_id": "12345678",
  "exam_code": "2942",
  "total_score": 9.0,
  "created_by": "user_id"
}
```

#### Update Exam
```http
PUT /exams/<exam_id>
Content-Type: application/json

{
  "total_score": 9.5
}
```

#### Delete Exam
```http
DELETE /exams/<exam_id>

Response:
{
  "message": "Exam deleted successfully"
}
```

---

### ✅ Correct Answers Management

#### Create Correct Answers from Images
```http
POST /correctans
Content-Type: multipart/form-data

exam_code: 2942
p1_img: <file>
p2_img: <file>
p3_img: <file>

Response:
{
  "message": "Correct answers created",
  "correctans_id": "...",
  "exam_code": "2942",
  "answers_count": 40
}
```

#### Create Correct Answers Manually
```http
POST /correctans/manual
Content-Type: application/json

{
  "exam_code": "2942",
  "answers": [
    [1, "A"],
    [2, "B"],
    [3, "C"],
    ...
  ]
}
```

#### Get Correct Answers
```http
GET /correctans/<exam_code>

Response:
{
  "exam_code": "2942",
  "answers": [[1, "A"], [2, "B"], ...],
  "answers_count": 40
}
```

#### Update Correct Answers
```http
PUT /correctans/<exam_code>
Content-Type: application/json

{
  "answers": [[1, "A"], [2, "B"], ...]
}
```

#### Delete Correct Answers
```http
DELETE /correctans/<exam_code>

Response:
{
  "message": "Correct answers deleted"
}
```

#### List All Correct Answers
```http
GET /correctans

Response:
[
  {
    "exam_code": "2942",
    "answers_count": 40
  }
]
```

---

### 🔍 Direct Scan Endpoints (Single-step)

For direct scanning without sessions:

#### Scan Student ID
```http
POST /scan/student_id
Content-Type: multipart/form-data

image: <file>

Response:
{
  "student_id": "12345678"
}
```

#### Scan Exam Code
```http
POST /scan/exam_code
Content-Type: multipart/form-data

image: <file>

Response:
{
  "exam_code": "2942"
}
```

#### Scan All Answers
```http
POST /scan/answers
Content-Type: multipart/form-data

p1_img: <file>
p2_img: <file>
p3_img: <file>

Response:
{
  "answers": [[1, "A"], [2, "B"], ...],
  "answers_count": 40
}
```

---

### 🏥 Health & Monitoring

#### Health Check
```http
GET /health

Response:
{
  "status": "healthy",
  "timestamp": "2025-10-06T10:00:00",
  "services": {
    "mongodb": "healthy",
    "redis": "not_configured"
  },
  "metrics": {
    "active_sessions": 5
  }
}
```

#### API Root
```http
GET /

Response:
{
  "name": "Exam Grading API",
  "version": "1.0.0",
  "endpoints": {
    "auth": "/auth/*",
    "exams": "/exams",
    "correctans": "/correctans",
    "sessions": "/exam/session/*",
    "scan": "/scan/*",
    "health": "/health"
  }
}
```

---

## 🎯 Usage Examples

### Complete Exam Processing Flow

```python
import requests

API_URL = "http://localhost:5000"

# 1. Start session
response = requests.post(f"{API_URL}/exam/session/start")
session_id = response.json()["session_id"]

# 2. Upload student ID
with open("student_id.jpg", "rb") as f:
    requests.post(
        f"{API_URL}/exam/session/student_id",
        data={"session_id": session_id},
        files={"image": f}
    )

# 3. Upload exam code
with open("exam_code.jpg", "rb") as f:
    requests.post(
        f"{API_URL}/exam/session/exam_code",
        data={"session_id": session_id},
        files={"image": f}
    )

# 4. Upload answer sheets
for part in ["p1", "p2", "p3"]:
    with open(f"{part}.jpg", "rb") as f:
        requests.post(
            f"{API_URL}/exam/session/part/{part}",
            data={"session_id": session_id},
            files={"image": f}
        )

# 5. Finish and get results
result = requests.post(
    f"{API_URL}/exam/session/finish",
    data={"session_id": session_id}
)
print(result.json())
```

### Create Correct Answers

```python
import requests

API_URL = "http://localhost:5000"

# From images
with open("p1.jpg", "rb") as f1, \
     open("p2.jpg", "rb") as f2, \
     open("p3.jpg", "rb") as f3:
    response = requests.post(
        f"{API_URL}/correctans",
        data={"exam_code": "2942"},
        files={
            "p1_img": f1,
            "p2_img": f2,
            "p3_img": f3
        }
    )
    print(response.json())

# Or manually
correct_answers = {
    "exam_code": "2942",
    "answers": [[i, "A"] for i in range(1, 41)]  # Example
}
response = requests.post(
    f"{API_URL}/correctans/manual",
    json=correct_answers
)
print(response.json())
```

---

## 🗂️ Project Structure

```
BE/
├── main.py                      # Main Flask application
├── requirements.txt             # Python dependencies
├── render.yaml                  # Deployment configuration
├── .env                         # Environment variables
├── Models/
│   ├── exam.py                  # Exam data model
│   ├── user.py                  # User data model
│   └── correctans.py            # Correct answers model
├── services/
│   ├── Auth/
│   │   └── auth_service.py      # Authentication logic
│   ├── Db/
│   │   ├── exam_db_service.py   # Exam database operations
│   │   └── correctans_db_service.py  # Correct answers DB ops
│   ├── Grade/
│   │   ├── create_ans.py        # Answer grading logic
│   │   └── scan_student_id.py   # Scan orchestration
│   └── Process/
│       ├── ec.py                # Exam code processing
│       ├── p1.py                # Part 1 answer processing
│       ├── p2.py                # Part 2 answer processing
│       └── p3.py                # Part 3 answer processing
└── utils.py                     # Utility functions
```

---

## 🔒 Error Handling

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid input)
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error

Error response format:
```json
{
  "error": "Description of the error"
}
```

---

## 🚀 Deployment

### Deploy to Render

The project includes `render.yaml` for easy deployment:

1. Connect your GitHub repository to Render
2. Render will automatically detect and deploy using the configuration
3. Set environment variables in Render dashboard

### Local Development

```bash
# Development mode with auto-reload
export FLASK_ENV=development
python main.py
```

---

## 📝 Notes

- **Image Format**: Accepts JPG, PNG images
- **Session Timeout**: Sessions expire after 30 minutes
- **Temp Files**: Automatically cleaned up after processing
- **Caching**: Correct answers are cached for performance
- **Logging**: All requests are logged with timestamps

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 📧 Contact

For issues or questions, please open an issue on GitHub.
