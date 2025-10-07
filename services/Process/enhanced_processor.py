#!/usr/bin/env python3
"""
Enhanced Image Processing Module
Advanced OCR and computer vision techniques for improved accuracy
"""
import cv2
import numpy as np
import pytesseract
import easyocr
from skimage import filters, morphology, measure
from skimage.filters import threshold_otsu, threshold_adaptive
from skimage.morphology import disk
import logging

logger = logging.getLogger(__name__)

class EnhancedImageProcessor:
    """Advanced image processing with multiple techniques for better accuracy"""

    def __init__(self):
        # Initialize OCR readers
        try:
            self.tesseract_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)  # CPU mode for compatibility
        except Exception as e:
            logger.warning(f"OCR initialization failed: {e}")
            self.easyocr_reader = None

    def advanced_preprocessing(self, image):
        """Advanced image preprocessing pipeline"""
        if image is None:
            return None

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Noise reduction
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)

        # Contrast enhancement using CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)

        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        cleaned = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)

        return cleaned

    def adaptive_thresholding(self, image, method='hybrid'):
        """Multiple thresholding approaches"""
        if method == 'hybrid':
            # Combine Otsu with adaptive thresholding
            otsu_thresh = threshold_otsu(image)
            adaptive_thresh = threshold_adaptive(image, block_size=11, offset=5)

            # Use Otsu for uniform areas, adaptive for varying areas
            combined = np.where(image > otsu_thresh, adaptive_thresh, 255)
            binary = (combined > image).astype(np.uint8) * 255

        elif method == 'otsu':
            thresh = threshold_otsu(image)
            binary = (image > thresh).astype(np.uint8) * 255

        elif method == 'adaptive':
            thresh = threshold_adaptive(image, block_size=15, offset=3)
            binary = (thresh > image).astype(np.uint8) * 255

        else:
            # Traditional OpenCV method
            binary = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY_INV, 11, 2)

        return binary

    def detect_bubbles_ensemble(self, image, expected_bubbles=4):
        """Ensemble bubble detection using multiple methods"""
        detections = []

        # Method 1: Contour detection (current approach)
        contours = self._detect_contours(image)
        detections.extend(self._filter_bubbles_by_contours(contours, expected_bubbles))

        # Method 2: Hough circle detection for perfect circles
        circles = self._detect_circles_hough(image)
        detections.extend(self._filter_bubbles_by_circles(circles))

        # Method 3: Template matching with multiple templates
        templates = self._create_bubble_templates()
        template_matches = self._detect_by_template_matching(image, templates)
        detections.extend(template_matches)

        # Method 4: Connected components analysis
        components = self._detect_connected_components(image)
        detections.extend(components)

        # Merge detections and remove duplicates
        merged = self._merge_detections(detections)

        return merged

    def _detect_contours(self, image):
        """Contour-based bubble detection"""
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bubble_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue

            circularity = 4 * np.pi * area / (perimeter * perimeter)

            # Filter for circular shapes
            if 500 < area < 5000 and 0.7 < circularity < 1.3:
                x, y, w, h = cv2.boundingRect(contour)
                bubble_contours.append({
                    'center': (x + w//2, y + h//2),
                    'bbox': (x, y, w, h),
                    'confidence': circularity,
                    'method': 'contour'
                })

        return bubble_contours

    def _detect_circles_hough(self, image):
        """Hough circle detection"""
        circles = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT, 1, 20,
                                 param1=50, param2=30, minRadius=10, maxRadius=25)

        detections = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                detections.append({
                    'center': (x, y),
                    'bbox': (x-r, y-r, 2*r, 2*r),
                    'confidence': 0.9,  # Hough circles are usually accurate
                    'method': 'hough'
                })

        return detections

    def _create_bubble_templates(self):
        """Create bubble templates for template matching"""
        templates = []

        # Create circular templates of different sizes
        for radius in range(12, 20):
            template = np.zeros((radius*2+10, radius*2+10), dtype=np.uint8)
            cv2.circle(template, (radius+5, radius+5), radius, 255, -1)
            templates.append(template)

        return templates

    def _detect_by_template_matching(self, image, templates):
        """Template matching for bubble detection"""
        detections = []

        for template in templates:
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.7
            locations = np.where(result >= threshold)

            for pt in zip(*locations[::-1]):
                detections.append({
                    'center': (pt[0] + template.shape[1]//2, pt[1] + template.shape[0]//2),
                    'bbox': (pt[0], pt[1], template.shape[1], template.shape[0]),
                    'confidence': result[pt[1], pt[0]],
                    'method': 'template'
                })

        return detections

    def _detect_connected_components(self, image):
        """Connected components analysis"""
        # Label connected components
        labeled = measure.label(image > 127, connectivity=2)
        properties = measure.regionprops(labeled)

        detections = []
        for prop in properties:
            area = prop.area
            if 500 < area < 5000:  # Similar size filter as contours
                y, x = prop.centroid
                minr, minc, maxr, maxc = prop.bbox
                w, h = maxc - minc, maxr - minr

                detections.append({
                    'center': (int(x), int(y)),
                    'bbox': (minc, minr, w, h),
                    'confidence': 0.8,
                    'method': 'components'
                })

        return detections

    def _merge_detections(self, detections, distance_threshold=15):
        """Merge nearby detections and remove duplicates"""
        if not detections:
            return []

        # Sort by confidence
        detections.sort(key=lambda x: x['confidence'], reverse=True)

        merged = []
        for detection in detections:
            # Check if this detection is close to any existing merged detection
            too_close = False
            for merged_det in merged:
                dist = np.sqrt((detection['center'][0] - merged_det['center'][0])**2 +
                             (detection['center'][1] - merged_det['center'][1])**2)
                if dist < distance_threshold:
                    too_close = True
                    break

            if not too_close:
                merged.append(detection)

        return merged

    def extract_text_ocr(self, image, region=None):
        """Extract text using multiple OCR engines"""
        if region:
            x, y, w, h = region
            roi = image[y:y+h, x:x+w]
        else:
            roi = image

        results = {}

        # Tesseract OCR
        try:
            tesseract_text = pytesseract.image_to_string(roi, config=self.tesseract_config).strip()
            results['tesseract'] = tesseract_text
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}")
            results['tesseract'] = ""

        # EasyOCR
        if self.easyocr_reader:
            try:
                easyocr_result = self.easyocr_reader.readtext(roi)
                easyocr_text = ' '.join([text for _, text, _ in easyocr_result])
                results['easyocr'] = easyocr_text.strip()
            except Exception as e:
                logger.warning(f"EasyOCR failed: {e}")
                results['easyocr'] = ""

        # Combine results (take the most confident one)
        best_text = ""
        if results.get('tesseract') and len(results['tesseract']) > len(best_text):
            best_text = results['tesseract']
        if results.get('easyocr') and len(results['easyocr']) > len(best_text):
            best_text = results['easyocr']

        return best_text, results

    def validate_bubble_fill(self, image, bubble_center, bubble_radius=15):
        """Advanced bubble fill validation"""
        x, y = bubble_center
        r = bubble_radius

        # Extract bubble region
        bubble_roi = image[max(0, y-r):min(image.shape[0], y+r),
                          max(0, x-r):min(image.shape[1], x+r)]

        if bubble_roi.size == 0:
            return False, 0.0

        # Multiple validation methods
        methods = {
            'pixel_ratio': self._validate_pixel_ratio(bubble_roi),
            'intensity': self._validate_intensity(bubble_roi),
            'edge_density': self._validate_edge_density(bubble_roi),
            'contour_fit': self._validate_contour_fit(bubble_roi)
        }

        # Ensemble decision
        weights = {'pixel_ratio': 0.4, 'intensity': 0.3, 'edge_density': 0.2, 'contour_fit': 0.1}
        total_score = sum(methods[method] * weights[method] for method in methods)

        # Threshold for filled bubble
        is_filled = total_score > 0.6

        return is_filled, total_score

    def _validate_pixel_ratio(self, roi):
        """Validate based on dark pixel ratio"""
        dark_pixels = np.sum(roi < 127)
        total_pixels = roi.size
        ratio = dark_pixels / total_pixels
        return min(ratio * 2.5, 1.0)  # Scale and cap

    def _validate_intensity(self, roi):
        """Validate based on mean intensity"""
        mean_intensity = np.mean(roi)
        # Lower intensity = darker = more likely filled
        score = 1.0 - (mean_intensity / 255.0)
        return score

    def _validate_edge_density(self, roi):
        """Validate based on edge density"""
        edges = cv2.Canny(roi, 50, 150)
        edge_density = np.sum(edges > 0) / roi.size
        # Moderate edge density is good for filled bubbles
        return 1.0 - abs(edge_density - 0.3) * 2

    def _validate_contour_fit(self, roi):
        """Validate based on how well contours fit a circle"""
        contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        # Find largest contour
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        perimeter = cv2.arcLength(largest, True)

        if perimeter == 0:
            return 0.0

        circularity = 4 * np.pi * area / (perimeter * perimeter)
        return min(circularity, 1.0)

    def process_image_enhanced(self, image_path):
        """Complete enhanced processing pipeline"""
        # Load and preprocess
        image = cv2.imread(image_path)
        if image is None:
            return None

        processed = self.advanced_preprocessing(image)

        # Multi-method thresholding
        binary = self.adaptive_thresholding(processed, method='hybrid')

        # Ensemble bubble detection
        bubbles = self.detect_bubbles_ensemble(binary)

        # Enhanced validation for each bubble
        validated_bubbles = []
        for bubble in bubbles:
            is_filled, confidence = self.validate_bubble_fill(processed, bubble['center'])
            if is_filled:
                validated_bubbles.append({
                    **bubble,
                    'fill_confidence': confidence
                })

        return {
            'original_image': image,
            'processed_image': processed,
            'binary_image': binary,
            'detected_bubbles': bubbles,
            'validated_bubbles': validated_bubbles
        }


# Singleton instance for reuse
enhanced_processor = EnhancedImageProcessor()


def get_enhanced_processor():
    """Get the enhanced image processor instance"""
    return enhanced_processor


if __name__ == "__main__":
    # Test the enhanced processor
    processor = get_enhanced_processor()

    # Test with sample image
    test_image = "services/Process/p12.jpg"
    if os.path.exists(test_image):
        result = processor.process_image_enhanced(test_image)
        if result:
            print(f"✅ Enhanced processing successful")
            print(f"   Detected bubbles: {len(result['detected_bubbles'])}")
            print(f"   Validated bubbles: {len(result['validated_bubbles'])}")
        else:
            print("❌ Enhanced processing failed")
    else:
        print(f"Test image not found: {test_image}")