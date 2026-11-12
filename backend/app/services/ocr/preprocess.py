import cv2
import numpy as np
from typing import Tuple, Dict, Any

def deskew_image(gray: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Detects skew angle in scanned documents and rotates image to be upright.
    Per Architecture Section 6.
    """
    # Invert image: text becomes white, background black
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    # Find all coordinates of text pixels
    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        return gray, 0.0

    # Determine minimum area bounding rectangle
    angle = cv2.minAreaRect(coords)[-1]

    # Adjust angle convention from OpenCV
    if angle < -45:
        angle = -(90 + angle)
    elif angle > 45:
        angle = 90 - angle
    else:
        angle = -angle

    # Only rotate if skew is non-trivial (> 0.5 degrees and < 45 degrees)
    if abs(angle) > 0.5 and abs(angle) < 45.0:
        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=255  # White background
        )
        return rotated, round(float(angle), 2)

    return gray, 0.0

def preprocess_image_for_ocr(image_bytes: bytes) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Complete OpenCV preprocessing pipeline:
    1. Grayscale conversion
    2. Scan noise reduction
    3. Deskewing
    4. Contrast enhancement (CLAHE)
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image bytes with OpenCV")

    h, w = img.shape[:2]

    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Deskew
    deskewed, angle = deskew_image(gray)

    # 3. Denoise with gentle Gaussian blur to preserve character edges
    denoised = cv2.GaussianBlur(deskewed, (3, 3), 0)

    # 4. Contrast enhancement using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    metadata = {
        "original_width": w,
        "original_height": h,
        "deskew_angle": angle,
        "processed_channels": 1
    }

    return enhanced, metadata
