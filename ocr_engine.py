"""
ocr_engine.py — Tesseract OCR processing with OpenCV image preprocessing.

Pipeline:
  1. Load uploaded image
  2. Preprocess (grayscale → blur → threshold → deskew)
  3. Run Tesseract OCR
  4. Return raw text for user review/correction
"""

import re
import io
import numpy as np
from PIL import Image

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

import sys
import os

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    # If running locally on Windows, set the explicit path
    if sys.platform == "win32":
        win_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(win_path):
            pytesseract.pytesseract.tesseract_cmd = win_path
    # On Cloud/Linux, pytesseract will automatically find it in the PATH
except ImportError:
    TESSERACT_AVAILABLE = False


def check_tesseract() -> tuple[bool, str]:
    """Check if Tesseract is available and return status + message."""
    if not TESSERACT_AVAILABLE:
        return False, (
            "❌ **pytesseract** is not installed.\n\n"
            "Run: `pip install pytesseract`"
        )

    try:
        version = pytesseract.get_tesseract_version()
        return True, f"✅ Tesseract v{version} detected"
    except Exception:
        return False, (
            "❌ **Tesseract OCR engine** is not installed or not in PATH.\n\n"
            "**Windows:** Download from "
            "[UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) "
            "and add to PATH.\n\n"
            "**After installing**, restart this app."
        )


def preprocess_image(image: Image.Image) -> tuple[Image.Image, np.ndarray]:
    """
    Preprocess a PIL image for better OCR accuracy.

    Returns:
        - processed PIL Image (for display)
        - processed numpy array (for OCR)
    """
    # Convert PIL to numpy array
    img_array = np.array(image)

    if not CV2_AVAILABLE:
        # Fallback: just convert to grayscale via PIL
        gray_image = image.convert("L")
        return gray_image, np.array(gray_image)

    # Convert to grayscale
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Apply Otsu's thresholding for binarization
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Deskew: detect skew angle and rotate
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) > 50:
        try:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            # Only deskew if angle is significant but not too extreme
            if abs(angle) > 0.5 and abs(angle) < 15:
                (h, w) = thresh.shape[:2]
                center = (w // 2, h // 2)
                matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                thresh = cv2.warpAffine(
                    thresh, matrix, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )
        except Exception:
            pass  # Skip deskew if it fails

    # Slight dilation to connect broken characters
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.dilate(thresh, kernel, iterations=1)

    # Convert back to PIL for display
    processed_pil = Image.fromarray(processed)

    return processed_pil, processed


def extract_text(image: Image.Image, psm: int = 6) -> str:
    """
    Run Tesseract OCR on a PIL image.

    Args:
        image: PIL Image to process
        psm: Page Segmentation Mode (default 6 = uniform text block)

    Returns:
        Extracted text string
    """
    if not TESSERACT_AVAILABLE:
        return "[ERROR] pytesseract is not installed"

    # Preprocess
    _, processed_array = preprocess_image(image)

    # Run Tesseract
    # Restrict to numbers, decimals, commas, and currency symbols
    custom_config = f"--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789.,₱"
    try:
        text = pytesseract.image_to_string(
            processed_array, config=custom_config
        )
        return text.strip()
    except Exception as e:
        return f"[ERROR] OCR failed: {str(e)}"


def detect_prices_from_text(raw_text: str) -> list[float]:
    """
    Extract all price-like numbers from OCR text.

    Looks for patterns like:
        ₱123.45, P123.45, 123.45, PHP 123.45, 1,234.56

    Returns a list of detected prices sorted by value (descending),
    filtered to reasonable grocery price range.
    """
    if not raw_text:
        return []

    # Multiple patterns to catch different price label formats
    patterns = [
        r'[₱P]\s*([\d,]+\.?\d{0,2})',          # ₱123.45 or P123.45
        r'PHP\s*([\d,]+\.?\d{0,2})',             # PHP 123.45
        r'(?:^|\s)([\d,]+\.\d{2})(?:\s|$)',      # 123.45 (with decimal)
        r'(?:price|srp|sale)\s*:?\s*([\d,]+\.?\d{0,2})',  # price: 123.45
    ]

    prices = set()
    for pattern in patterns:
        matches = re.findall(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            try:
                price = float(match.replace(",", ""))
                if 0.5 < price < 100000:  # Reasonable grocery price range
                    prices.add(price)
            except ValueError:
                continue

    # Also try to find standalone numbers that look like prices
    standalone = re.findall(r'(?:^|\s)([\d]{1,6}\.?\d{0,2})(?:\s|$)', raw_text, re.MULTILINE)
    for match in standalone:
        try:
            price = float(match)
            if 1 < price < 100000:
                prices.add(price)
        except ValueError:
            continue

    return sorted(prices, reverse=True)

