#!/usr/bin/env python3
"""
Accuracy Testing Framework
Comprehensive testing and comparison of exam grading accuracy
"""
import os
import sys
import cv2
import numpy as np
import json
import time
from datetime import datetime
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.Process.p1 import process_p1_answers
from services.Process.p2 import process_p2_answers
from services.Process.p3 import process_p3_answers

logger = logging.getLogger(__name__)

class AccuracyTester:
    """Comprehensive accuracy testing framework"""

    def __init__(self, test_images_dir=None, ground_truth_file=None):
        """
        Initialize accuracy tester

        Args:
            test_images_dir: Directory containing test exam images
            ground_truth_file: JSON file with correct answers for comparison
        """
        self.test_images_dir = test_images_dir or os.path.join(
            os.path.dirname(__file__), 'test_images'
        )
        self.ground_truth_file = ground_truth_file or os.path.join(
            os.path.dirname(__file__), 'ground_truth.json'
        )
        self.results_dir = os.path.join(os.path.dirname(__file__), 'test_results')
        os.makedirs(self.results_dir, exist_ok=True)

    def load_ground_truth(self):
        """Load ground truth answers for comparison"""
        if os.path.exists(self.ground_truth_file):
            with open(self.ground_truth_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_ground_truth(self, ground_truth):
        """Save ground truth answers"""
        with open(self.ground_truth_file, 'w', encoding='utf-8') as f:
            json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    def find_test_images(self):
        """Find all test images in the test directory"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        test_images = []

        if os.path.exists(self.test_images_dir):
            for file in os.listdir(self.test_images_dir):
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    test_images.append(os.path.join(self.test_images_dir, file))

        # Also check process directory for sample images
        process_dir = os.path.join(os.path.dirname(__file__), 'services', 'Process')
        sample_images = ['p12.jpg', 'p23.jpg', 'test.jpg']
        for img in sample_images:
            img_path = os.path.join(process_dir, img)
            if os.path.exists(img_path):
                test_images.append(img_path)

        return list(set(test_images))  # Remove duplicates

    def test_single_image(self, image_path, enable_ocr=False):
        """
        Test processing accuracy for a single image

        Args:
            image_path: Path to exam image
            enable_ocr: Enable OCR validation

        Returns:
            dict: Test results
        """
        results = {
            'image_path': image_path,
            'image_name': os.path.basename(image_path),
            'timestamp': datetime.now().isoformat(),
            'processing_time': 0,
            'sections': {},
            'errors': []
        }

        start_time = time.time()

        try:
            # Test P1 (Multiple Choice)
            p1_results = process_p1_answers(image_path, enable_ocr_validation=enable_ocr)
            results['sections']['p1'] = {
                'answers': p1_results['answers'],
                'validation': p1_results.get('validation'),
                'answer_count': len([a for q, a in p1_results['answers'] if a])
            }

        except Exception as e:
            results['errors'].append(f'P1 processing failed: {e}')
            results['sections']['p1'] = {'error': str(e)}

        try:
            # Test P2 (True/False)
            p2_results = process_p2_answers(image_path)
            results['sections']['p2'] = {
                'answers': p2_results,
                'answer_count': len([a for q, a in p2_results if a])
            }

        except Exception as e:
            results['errors'].append(f'P2 processing failed: {e}')
            results['sections']['p2'] = {'error': str(e)}

        try:
            # Test P3 (Essay)
            p3_results = process_p3_answers(image_path)
            results['sections']['p3'] = {
                'answers': p3_results,
                'answer_count': len([a for q, a in p3_results if a[1]])
            }

        except Exception as e:
            results['errors'].append(f'P3 processing failed: {e}')
            results['sections']['p3'] = {'error': str(e)}

        results['processing_time'] = time.time() - start_time
        return results

    def compare_with_ground_truth(self, test_results, ground_truth):
        """
        Compare test results with ground truth

        Args:
            test_results: Results from test_single_image
            ground_truth: Correct answers dictionary

        Returns:
            dict: Comparison metrics
        """
        comparison = {
            'image_name': test_results['image_name'],
            'sections': {},
            'overall_accuracy': 0.0,
            'total_questions': 0,
            'correct_answers': 0
        }

        image_gt = ground_truth.get(test_results['image_name'], {})

        for section_name, section_results in test_results['sections'].items():
            if 'error' in section_results:
                comparison['sections'][section_name] = {'error': section_results['error']}
                continue

            section_gt = image_gt.get(section_name, {})
            detected_answers = section_results.get('answers', [])

            section_comparison = {
                'total_questions': len(detected_answers),
                'correct_answers': 0,
                'accuracy': 0.0,
                'details': []
            }

            for q_num, detected_ans in detected_answers:
                correct_ans = section_gt.get(str(q_num))
                is_correct = detected_ans == correct_ans

                section_comparison['details'].append({
                    'question': q_num,
                    'detected': detected_ans,
                    'correct': correct_ans,
                    'is_correct': is_correct
                })

                if is_correct:
                    section_comparison['correct_answers'] += 1

            if section_comparison['total_questions'] > 0:
                section_comparison['accuracy'] = (
                    section_comparison['correct_answers'] / section_comparison['total_questions']
                )

            comparison['sections'][section_name] = section_comparison
            comparison['total_questions'] += section_comparison['total_questions']
            comparison['correct_answers'] += section_comparison['correct_answers']

        if comparison['total_questions'] > 0:
            comparison['overall_accuracy'] = (
                comparison['correct_answers'] / comparison['total_questions']
            )

        return comparison

    def run_accuracy_tests(self, enable_ocr=False, save_results=True):
        """
        Run comprehensive accuracy tests

        Args:
            enable_ocr: Enable OCR validation
            save_results: Save results to file

        Returns:
            dict: Complete test results
        """
        print("🧪 Starting Accuracy Tests")
        print("=" * 50)

        test_images = self.find_test_images()
        ground_truth = self.load_ground_truth()

        print(f"Found {len(test_images)} test images")
        print(f"Ground truth available: {'Yes' if ground_truth else 'No'}")

        all_results = {
            'test_run': {
                'timestamp': datetime.now().isoformat(),
                'ocr_enabled': enable_ocr,
                'test_images_count': len(test_images),
                'ground_truth_available': bool(ground_truth)
            },
            'individual_results': [],
            'comparisons': [],
            'summary': {}
        }

        for i, image_path in enumerate(test_images, 1):
            print(f"\n📸 Testing image {i}/{len(test_images)}: {os.path.basename(image_path)}")

            # Run processing test
            test_results = self.test_single_image(image_path, enable_ocr=enable_ocr)
            all_results['individual_results'].append(test_results)

            print(f"  Processing time: {test_results['processing_time']:.2f}s")

            # Compare with ground truth if available
            if ground_truth:
                comparison = self.compare_with_ground_truth(test_results, ground_truth)
                all_results['comparisons'].append(comparison)
                print(f"  Accuracy: {comparison['overall_accuracy']:.1%}")

        # Generate summary
        if all_results['individual_results']:
            all_results['summary'] = self.generate_summary(all_results)

        # Save results
        if save_results:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = os.path.join(self.results_dir, f'accuracy_test_{timestamp}.json')
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to: {result_file}")

        print("\n🎉 Accuracy testing completed!")
        return all_results

    def generate_summary(self, all_results):
        """Generate summary statistics from test results"""
        summary = {
            'total_images': len(all_results['individual_results']),
            'average_processing_time': 0.0,
            'section_performance': {},
            'error_count': 0
        }

        total_time = 0
        section_stats = {}

        for result in all_results['individual_results']:
            total_time += result['processing_time']
            summary['error_count'] += len(result['errors'])

            for section_name, section_data in result['sections'].items():
                if section_name not in section_stats:
                    section_stats[section_name] = {
                        'total_tests': 0,
                        'successful_tests': 0,
                        'average_answers': 0.0
                    }

                section_stats[section_name]['total_tests'] += 1

                if 'error' not in section_data:
                    section_stats[section_name]['successful_tests'] += 1
                    section_stats[section_name]['average_answers'] += section_data.get('answer_count', 0)

        summary['average_processing_time'] = total_time / len(all_results['individual_results'])

        for section_name, stats in section_stats.items():
            if stats['successful_tests'] > 0:
                stats['average_answers'] /= stats['successful_tests']
            summary['section_performance'][section_name] = stats

        # Accuracy summary if comparisons available
        if all_results['comparisons']:
            accuracy_stats = {
                'total_comparisons': len(all_results['comparisons']),
                'average_accuracy': 0.0,
                'section_accuracies': {}
            }

            section_accuracies = {}

            for comparison in all_results['comparisons']:
                accuracy_stats['average_accuracy'] += comparison['overall_accuracy']

                for section_name, section_comp in comparison['sections'].items():
                    if 'error' not in section_comp:
                        if section_name not in section_accuracies:
                            section_accuracies[section_name] = []
                        section_accuracies[section_name].append(section_comp['accuracy'])

            accuracy_stats['average_accuracy'] /= len(all_results['comparisons'])

            for section_name, accuracies in section_accuracies.items():
                accuracy_stats['section_accuracies'][section_name] = {
                    'average': np.mean(accuracies),
                    'min': np.min(accuracies),
                    'max': np.max(accuracies),
                    'std': np.std(accuracies)
                }

            summary['accuracy_stats'] = accuracy_stats

        return summary

    def create_ground_truth_template(self, test_images=None):
        """
        Create a template ground truth file for manual annotation

        Args:
            test_images: List of image paths (if None, auto-discover)
        """
        if test_images is None:
            test_images = self.find_test_images()

        template = {}

        for image_path in test_images:
            image_name = os.path.basename(image_path)
            print(f"Processing {image_name}...")

            # Run processing to get detected answers as template
            try:
                p1_results = process_p1_answers(image_path)
                p2_results = process_p2_answers(image_path)
                p3_results = process_p3_answers(image_path)

                template[image_name] = {
                    'p1': {str(q): a for q, a in p1_results['answers']},
                    'p2': {str(q.split('_')[1]): a for q, a in p2_results},
                    'p3': {str(q.split('_')[1]): a for q, a in p3_results}
                }

            except Exception as e:
                print(f"Error processing {image_name}: {e}")
                template[image_name] = {'error': str(e)}

        # Save template
        template_file = os.path.join(self.results_dir, 'ground_truth_template.json')
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)

        print(f"Ground truth template saved to: {template_file}")
        print("Please review and correct the answers manually, then rename to ground_truth.json")

        return template


def main():
    """Main function for command line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Exam Grading Accuracy Tester')
    parser.add_argument('--test-dir', help='Directory containing test images')
    parser.add_argument('--ground-truth', help='Ground truth JSON file')
    parser.add_argument('--ocr', action='store_true', help='Enable OCR validation')
    parser.add_argument('--create-template', action='store_true',
                       help='Create ground truth template instead of testing')

    args = parser.parse_args()

    tester = AccuracyTester(args.test_dir, args.ground_truth)

    if args.create_template:
        print("Creating ground truth template...")
        tester.create_ground_truth_template()
    else:
        print("Running accuracy tests...")
        results = tester.run_accuracy_tests(enable_ocr=args.ocr)

        # Print summary
        summary = results.get('summary', {})
        print("\n📊 Test Summary:")
        print(f"Images tested: {summary.get('total_images', 0)}")
        print(f"Average processing time: {summary.get('average_processing_time', 0):.2f}s")
        print(f"Errors: {summary.get('error_count', 0)}")

        if 'accuracy_stats' in summary:
            acc = summary['accuracy_stats']
            print(f"Average accuracy: {acc.get('average_accuracy', 0):.1%}")

if __name__ == "__main__":
    main()