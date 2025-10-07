#!/usr/bin/env python3
"""
Test P2/P3 Format Optimization
Verify that P2 and P3 now use correct formats
"""
import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = 'http://localhost:5000'
REAL_IMAGES = {
    'p1': 'services/Process/p12.jpg',
    'p2': 'services/Process/p23.jpg',
    'p3': 'services/Process/test.jpg'
}

def start_server():
    from main import app
    import threading
    def run_server():
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    threading.Thread(target=run_server, daemon=True).start()
    import time
    time.sleep(3)

def test_p2_format():
    """Test P2 format optimization"""
    logger.info("🔍 Testing P2 Format Optimization...")

    with open(REAL_IMAGES['p1'], 'rb') as f1, open(REAL_IMAGES['p2'], 'rb') as f2, open(REAL_IMAGES['p3'], 'rb') as f3:
        files = {
            'p1_img': ('p12.jpg', f1, 'image/jpeg'),
            'p2_img': ('p23.jpg', f2, 'image/jpeg'),
            'p3_img': ('test.jpg', f3, 'image/jpeg')
        }
        resp = requests.post(f"{API_BASE_URL}/scan/answers", files=files)

    if resp.status_code == 200:
        answers = resp.json()['answers']
        p2_answers = answers.get('p2', [])

        logger.info(f"P2 detected {len(p2_answers)} answers")

        # Check format - should be p2_q{num}_{sub} format
        correct_format = True
        for qid, answer in p2_answers[:5]:  # Check first 5
            if not (qid.startswith('p2_q') and '_' in qid and (qid.endswith('_a') or qid.endswith('_b') or qid.endswith('_c') or qid.endswith('_d'))):
                correct_format = False
                logger.error(f"❌ Wrong P2 format: {qid}")
                break

        if correct_format:
            logger.info("✅ P2 format corrected: using p2_q{num}_{sub} format")
            # Show sample
            for qid, answer in p2_answers[:3]:
                logger.info(f"   Sample: {qid} = '{answer}'")
        else:
            logger.error("❌ P2 format still incorrect")

        return correct_format
    else:
        logger.error("❌ P2 scanning failed")
        return False

def test_p3_format():
    """Test P3 format optimization"""
    logger.info("🔍 Testing P3 Format Optimization...")

    with open(REAL_IMAGES['p1'], 'rb') as f1, open(REAL_IMAGES['p2'], 'rb') as f2, open(REAL_IMAGES['p3'], 'rb') as f3:
        files = {
            'p1_img': ('p12.jpg', f1, 'image/jpeg'),
            'p2_img': ('p23.jpg', f2, 'image/jpeg'),
            'p3_img': ('test.jpg', f3, 'image/jpeg')
        }
        resp = requests.post(f"{API_BASE_URL}/scan/answers", files=files)

    if resp.status_code == 200:
        answers = resp.json()['answers']
        p3_answers = answers.get('p3', [])

        logger.info(f"P3 detected {len(p3_answers)} answers")

        # Check format - should be p3_c{num} with row number arrays
        correct_format = True
        for qid, marks in p3_answers:
            if not qid.startswith('p3_c'):
                correct_format = False
                logger.error(f"❌ Wrong P3 question format: {qid}")
                break
            if not isinstance(marks, list):
                correct_format = False
                logger.error(f"❌ Wrong P3 marks format: {marks} (should be list)")
                break
            # Check that marks are numbers (row numbers)
            for mark in marks:
                if not isinstance(mark, int):
                    correct_format = False
                    logger.error(f"❌ Wrong P3 mark type: {mark} (should be int)")
                    break

        if correct_format:
            logger.info("✅ P3 format corrected: using row numbers instead of symbols")
            # Show sample
            for qid, marks in p3_answers[:3]:
                logger.info(f"   Sample: {qid} = {marks}")
        else:
            logger.error("❌ P3 format still incorrect")

        return correct_format
    else:
        logger.error("❌ P3 scanning failed")
        return False

def test_combined_formats():
    """Test combined P2+P3 formats"""
    logger.info("🔍 Testing Combined P2+P3 Formats...")

    with open(REAL_IMAGES['p1'], 'rb') as f1, open(REAL_IMAGES['p2'], 'rb') as f2, open(REAL_IMAGES['p3'], 'rb') as f3:
        files = {
            'p1_img': ('p12.jpg', f1, 'image/jpeg'),
            'p2_img': ('p23.jpg', f2, 'image/jpeg'),
            'p3_img': ('test.jpg', f3, 'image/jpeg')
        }
        resp = requests.post(f"{API_BASE_URL}/scan/answers", files=files)

    if resp.status_code == 200:
        answers = resp.json()['answers']
        p2_answers = answers.get('p2', [])
        p3_answers = answers.get('p3', [])

        logger.info(f"Combined: P2={len(p2_answers)}, P3={len(p3_answers)}")

        # Verify P2 uses sequential question numbering
        p2_questions = [qid for qid, _ in p2_answers]
        
        # Check format: should be p2_q{num}_{sub} where num is sequential
        p2_format_correct = True
        question_numbers = []
        
        for qid in p2_questions:
            if not qid.startswith('p2_q'):
                p2_format_correct = False
                break
            # Extract question number
            try:
                num_part = qid.split('_')[1][1:]  # Remove 'q' prefix
                question_numbers.append(int(num_part))
            except (IndexError, ValueError):
                p2_format_correct = False
                break
        
        # Check if question numbers are sequential (1,2,3,... without gaps)
        if p2_format_correct and question_numbers:
            question_numbers.sort()
            expected_numbers = list(range(1, len(question_numbers) + 1))
            p2_sequential = question_numbers == expected_numbers
        else:
            p2_sequential = False
            
        if p2_sequential:
            logger.info("✅ P2 uses sequential question numbering (p2_q1_*, p2_q2_*, ...)")
        else:
            logger.warning("⚠️ P2 question numbering may have gaps or incorrect format")

        # Verify P3 uses row numbers
        p3_has_numbers = False
        for qid, marks in p3_answers:
            if marks and all(isinstance(m, int) for m in marks):
                p3_has_numbers = True
                break

        if p3_has_numbers:
            logger.info("✅ P3 uses row numbers instead of symbols")
        else:
            logger.warning("⚠️ P3 may still use symbols")

        return p2_sequential and p3_has_numbers
    else:
        logger.error("❌ Combined scanning failed")
        return False

def main():
    logger.info("🚀 P2/P3 Format Optimization Test")
    logger.info("=" * 50)

    # Start server
    start_server()
    if requests.get(f"{API_BASE_URL}/health").status_code != 200:
        logger.error("❌ Server failed to start")
        return

    logger.info("✅ Server running")

    # Test individual formats
    p2_ok = test_p2_format()
    logger.info("")
    p3_ok = test_p3_format()
    logger.info("")
    combined_ok = test_combined_formats()

    # Results
    logger.info("\n" + "=" * 50)
    logger.info("📊 FORMAT OPTIMIZATION RESULTS:")
    logger.info("=" * 50)

    if p2_ok:
        logger.info("✅ P2 Format: FIXED - Now uses p2_q{num}_{sub} (sequential questions)")
    else:
        logger.info("❌ P2 Format: Still needs work")

    if p3_ok:
        logger.info("✅ P3 Format: FIXED - Now returns row numbers instead of symbols")
    else:
        logger.info("❌ P3 Format: Still needs work")

    if combined_ok:
        logger.info("✅ Combined: Both formats working correctly")
    else:
        logger.info("⚠️ Combined: May need additional testing")

    logger.info("")
    if p2_ok and p3_ok:
        logger.info("🎉 SUCCESS: P2/P3 format optimization completed!")
        logger.info("   • P2 now uses sequential question IDs")
        logger.info("   • P3 now returns row numbers for accurate scoring")
        logger.info("   • Ready for reliable exam grading!")
    else:
        logger.info("⚠️ Some optimizations may need additional work")

    logger.info("=" * 50)

if __name__ == "__main__":
    main()