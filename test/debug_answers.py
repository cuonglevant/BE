#!/usr/bin/env python3
"""
Debug script to check what answers are actually scanned from real images
and compare with correct answers
"""
import os
import requests
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = 'http://localhost:5000'

# Real image paths
REAL_IMAGES = {
    'exam_code': 'services/Process/code.jpg',
    'p1': 'services/Process/p12.jpg',
    'p2': 'services/Process/p23.jpg',
    'p3': 'services/Process/test.jpg'
}

def start_server():
    """Start the Flask server in a separate thread"""
    from main import app
    import threading
    import time

    def run_server():
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(3)  # Give server time to start
    return server_thread

def debug_answer_scanning():
    """Debug what answers are actually scanned from real images"""
    logger.info("🔍 Debugging Answer Scanning from Real Images")
    logger.info("=" * 60)

    # Test individual scanning first
    logger.info("Testing individual answer scanning...")

    # Test P1 scanning
    with open(REAL_IMAGES['p1'], 'rb') as f:
        files = {'p1_img': ('p12.jpg', f, 'image/jpeg')}
        response = requests.post(f"{API_BASE_URL}/scan/answers", files=files)

    if response.status_code == 200:
        data = response.json()
        answers = data.get('answers', {})
        p1_answers = answers.get('p1', [])
        logger.info(f"P1 scanned answers: {p1_answers}")
        logger.info(f"P1 count: {len(p1_answers)}")
    else:
        logger.error(f"P1 scan failed: {response.status_code} - {response.text}")

    # Test combined scanning
    logger.info("\nTesting combined answer scanning...")
    with open(REAL_IMAGES['p1'], 'rb') as f1, \
         open(REAL_IMAGES['p2'], 'rb') as f2, \
         open(REAL_IMAGES['p3'], 'rb') as f3:

        files = {
            'p1_img': ('p12.jpg', f1, 'image/jpeg'),
            'p2_img': ('p23.jpg', f2, 'image/jpeg'),
            'p3_img': ('test.jpg', f3, 'image/jpeg')
        }

        response = requests.post(f"{API_BASE_URL}/scan/answers", files=files)

    if response.status_code == 200:
        data = response.json()
        answers = data.get('answers', {})
        logger.info("Combined scanned answers:")
        logger.info(f"  P1: {answers.get('p1', [])}")
        logger.info(f"  P2: {answers.get('p2', [])}")
        logger.info(f"  P3: {answers.get('p3', [])}")
        logger.info(f"  Counts - P1: {len(answers.get('p1', []))}, P2: {len(answers.get('p2', []))}, P3: {len(answers.get('p3', []))}")
    else:
        logger.error(f"Combined scan failed: {response.status_code} - {response.text}")

def debug_correct_answers():
    """Debug what correct answers are stored"""
    logger.info("\n🔍 Debugging Correct Answers")
    logger.info("=" * 60)

    # Get correct answers for REAL001
    response = requests.get(f"{API_BASE_URL}/correctans/REAL001")

    if response.status_code == 200:
        data = response.json()
        correct_answers = data.get('answers', {})
        logger.info("Correct answers for REAL001:")
        logger.info(f"  P1: {correct_answers.get('p1', [])}")
        logger.info(f"  P2: {correct_answers.get('p2', [])}")
        logger.info(f"  P3: {correct_answers.get('p3', [])}")
        logger.info(f"  Counts - P1: {len(correct_answers.get('p1', []))}, P2: {len(correct_answers.get('p2', []))}, P3: {len(correct_answers.get('p3', []))}")
    else:
        logger.error(f"Failed to get correct answers: {response.status_code} - {response.text}")

def debug_scoring():
    """Debug the scoring calculation"""
    logger.info("\n🔍 Debugging Scoring Calculation")
    logger.info("=" * 60)

    # Get scanned answers
    with open(REAL_IMAGES['p1'], 'rb') as f1, \
         open(REAL_IMAGES['p2'], 'rb') as f2, \
         open(REAL_IMAGES['p3'], 'rb') as f3:

        files = {
            'p1_img': ('p12.jpg', f1, 'image/jpeg'),
            'p2_img': ('p23.jpg', f2, 'image/jpeg'),
            'p3_img': ('test.jpg', f3, 'image/jpeg')
        }

        scan_response = requests.post(f"{API_BASE_URL}/scan/answers", files=files)

    if scan_response.status_code != 200:
        logger.error("Failed to scan answers for scoring debug")
        return

    scanned_answers = scan_response.json().get('answers', {})

    # Get correct answers
    correct_response = requests.get(f"{API_BASE_URL}/correctans/REAL001")

    if correct_response.status_code != 200:
        logger.error("Failed to get correct answers for scoring debug")
        return

    correct_answers = correct_response.json().get('answers', {})

    # Manual scoring calculation
    logger.info("Manual scoring calculation:")

    # P1 scoring
    if 'p1' in scanned_answers and 'p1' in correct_answers:
        p1_scanned = scanned_answers['p1']
        p1_correct = correct_answers['p1']
        correct_dict = dict(p1_correct)

        logger.info(f"P1 Scanned: {p1_scanned}")
        logger.info(f"P1 Correct: {p1_correct}")
        logger.info(f"P1 Correct Dict: {correct_dict}")

        correct_count = 0
        for q, a in p1_scanned:
            if q in correct_dict and a == correct_dict[q]:
                correct_count += 1
                logger.info(f"  ✓ Question {q}: '{a}' matches correct '{correct_dict[q]}'")
            else:
                logger.info(f"  ✗ Question {q}: '{a}' vs correct '{correct_dict.get(q, 'N/A')}'")

        p1_score = (correct_count / len(p1_correct)) * 10 if p1_correct else 0
        logger.info(f"P1: {correct_count}/{len(p1_correct)} correct = {p1_score:.2f}/10")

    # P2 scoring
    if 'p2' in scanned_answers and 'p2' in correct_answers:
        p2_scanned = scanned_answers['p2']
        p2_correct = correct_answers['p2']
        correct_dict = dict(p2_correct)

        logger.info(f"P2 Scanned: {p2_scanned}")
        logger.info(f"P2 Correct: {p2_correct}")

        correct_count = 0
        for qid, a in p2_scanned:
            if qid in correct_dict and a == correct_dict[qid]:
                correct_count += 1
                logger.info(f"  ✓ {qid}: '{a}' matches correct '{correct_dict[qid]}'")
            else:
                logger.info(f"  ✗ {qid}: '{a}' vs correct '{correct_dict.get(qid, 'N/A')}'")

        p2_score = (correct_count / len(p2_correct)) * 10 if p2_correct else 0
        logger.info(f"P2: {correct_count}/{len(p2_correct)} correct = {p2_score:.2f}/10")

    # P3 scoring
    if 'p3' in scanned_answers and 'p3' in correct_answers:
        p3_scanned = scanned_answers['p3']
        p3_correct = correct_answers['p3']
        correct_dict = {qid: marks for qid, marks in p3_correct}

        logger.info(f"P3 Scanned: {p3_scanned}")
        logger.info(f"P3 Correct: {p3_correct}")

        correct_count = 0
        for qid, marks in p3_scanned:
            if qid in correct_dict:
                expected_marks = set(correct_dict[qid])
                scanned_marks = set(marks)
                if expected_marks.issubset(scanned_marks):
                    correct_count += 1
                    logger.info(f"  ✓ {qid}: {marks} contains expected {list(expected_marks)}")
                else:
                    logger.info(f"  ✗ {qid}: {marks} missing expected {list(expected_marks)}")
            else:
                logger.info(f"  ✗ {qid}: not in correct answers")

        p3_score = (correct_count / len(p3_correct)) * 10 if p3_correct else 0
        logger.info(f"P3: {correct_count}/{len(p3_correct)} correct = {p3_score:.2f}/10")

if __name__ == "__main__":
    logger.info("🔧 Starting Answer Scanning Debug")
    logger.info("=" * 70)

    # Start server
    logger.info("Starting API server...")
    server_thread = start_server()

    # Test server health
    import time
    time.sleep(2)
    try:
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            logger.info("✅ API server is running")
        else:
            logger.error("❌ API server not responding properly")
            exit(1)
    except Exception as e:
        logger.error(f"❌ Cannot connect to API server: {e}")
        exit(1)

    # Run debug tests
    debug_answer_scanning()
    debug_correct_answers()
    debug_scoring()

    logger.info("\n" + "=" * 70)
    logger.info("🔧 Debug Complete")
    logger.info("=" * 70)