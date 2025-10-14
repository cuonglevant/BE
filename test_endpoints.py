#!/usr/bin/env python3
"""
Simple endpoint test - verifies the API works with new OMR processors
"""
import requests
from pathlib import Path

BASE_URL = "http://localhost:5000"
IMAGE_DIR = Path(__file__).parent / "2912"


def test_grade_exam():
    """Test the /grade/exam endpoint with actual images"""
    print("\n=== Testing /grade/exam endpoint ===")
    
    # Find test images
    p12_images = sorted(IMAGE_DIR.glob("p12_*.jpg"))
    p23_images = sorted(IMAGE_DIR.glob("p23_*.jpg"))
    code_images = sorted(IMAGE_DIR.glob("code*.jpg"))
    
    if not p12_images or not p23_images or not code_images:
        print("❌ Test images not found in 2912 folder")
        return False
    
    # Use first available images (excluding crops)
    p12_img = next((img for img in p12_images if 'crop' not in img.name), p12_images[0])
    p23_img = next((img for img in p23_images if 'crop' not in img.name), p23_images[0])
    code_img = code_images[0]
    
    print(f"Using images:")
    print(f"  Code: {code_img.name}")
    print(f"  P12: {p12_img.name}")
    print(f"  P23: {p23_img.name}")
    
    # Prepare files
    files = {
        'exam_code_img': open(code_img, 'rb'),
        'p1_img': open(p12_img, 'rb'),
        'p2_img': open(p12_img, 'rb'),
        'p3_img': open(p23_img, 'rb')
    }
    
    try:
        response = requests.post(f"{BASE_URL}/grade/exam", files=files)
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Success!")
            print(f"   Exam Code: {data.get('exam_code')}")
            print(f"   P1 Score: {data.get('p1_score')}")
            print(f"   P2 Score: {data.get('p2_score')}")
            print(f"   P3 Score: {data.get('p3_score')}")
            print(f"   Total Score: {data.get('total_score')}")
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        for f in files.values():
            f.close()


def test_scan_answers():
    """Test the /scan/answers endpoint"""
    print("\n=== Testing /scan/answers endpoint ===")
    
    p12_images = sorted(IMAGE_DIR.glob("p12_*.jpg"))
    p23_images = sorted(IMAGE_DIR.glob("p23_*.jpg"))
    
    if not p12_images or not p23_images:
        print("❌ Test images not found")
        return False
    
    p12_img = next((img for img in p12_images if 'crop' not in img.name), p12_images[0])
    p23_img = next((img for img in p23_images if 'crop' not in img.name), p23_images[0])
    
    files = {
        'p1_img': open(p12_img, 'rb'),
        'p2_img': open(p12_img, 'rb'),
        'p3_img': open(p23_img, 'rb')
    }
    
    try:
        response = requests.post(f"{BASE_URL}/scan/answers", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")
            print(f"   P1 answers: {len(data.get('p1', []))} detected")
            print(f"   P2 answers: {len(data.get('p2', []))} detected")
            print(f"   P3 answers: {len(data.get('p3', []))} detected")
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        for f in files.values():
            f.close()


def main():
    print("=" * 70)
    print("ENDPOINT VERIFICATION TEST")
    print("=" * 70)
    print("\nNOTE: Make sure the Flask server is running on http://localhost:5000")
    print("      Run: python main.py")
    
    input("\nPress Enter to start tests...")
    
    results = []
    
    # Test scan answers endpoint
    results.append(("Scan Answers", test_scan_answers()))
    
    # Test grade exam endpoint
    results.append(("Grade Exam", test_grade_exam()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 ALL TESTS PASSED!" if all_passed else "❌ SOME TESTS FAILED"))
    print("=" * 70)


if __name__ == '__main__':
    main()
