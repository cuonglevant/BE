#!/usr/bin/env python3
"""
Setup test data - Add correct answers to database
"""
import json
from services.Db.correctans_db_service import CorrectAnsDbService
from Models.correctans import CorrectAns

def setup_correct_answers():
    """Load validation data and create correct answers in database"""
    print("Loading validation data...")
    
    with open('validation_clean/validation_results.json', 'r') as f:
        validation = json.load(f)
    
    # Format P1 answers
    p1_answers = [(q['question'], q['answer']) for q in validation['part1']]
    
    # Format P2 answers
    p2_answers = []
    for q in validation['part2']:
        q_num = q['question']
        opts = q['answers']
        for opt_letter, opt_value in opts.items():
            p2_answers.append((f"q{q_num}_{opt_letter}", opt_value))
    
    # Format P3 answers
    p3_answers = [(q['question'], q['answer']) for q in validation['part3']]
    
    # Create correct answers object
    answers_dict = {
        'p1': p1_answers,
        'p2': p2_answers,
        'p3': p3_answers
    }
    
    print(f"P1 answers: {len(p1_answers)}")
    print(f"P2 answers: {len(p2_answers)}")
    print(f"P3 answers: {len(p3_answers)}")
    
    # Try different exam codes that might be scanned
    exam_codes = ['2412', '2912', '1457', 'DEFAULT_TEST']
    
    for exam_code in exam_codes:
        try:
            # Check if already exists
            existing = CorrectAnsDbService.get_correct_ans_by_exam_code(exam_code)
            if existing:
                print(f"✓ Correct answers already exist for exam code: {exam_code}")
            else:
                correct_ans = CorrectAns(id=exam_code, answers=answers_dict)
                result = CorrectAnsDbService.create_correct_ans(correct_ans)
                print(f"✓ Created correct answers for exam code: {exam_code} (ID: {result})")
        except Exception as e:
            print(f"✗ Error creating correct answers for {exam_code}: {e}")
    
    print("\n✅ Setup complete!")


if __name__ == '__main__':
    setup_correct_answers()
