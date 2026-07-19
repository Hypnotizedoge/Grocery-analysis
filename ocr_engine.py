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

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
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
    custom_config = f"--psm {psm} --oem 3"
    try:
        text = pytesseract.image_to_string(
            processed_array, config=custom_config
        )
        return text.strip()
    except Exception as e:
        return f"[ERROR] OCR failed: {str(e)}"


def parse_receipt_lines(raw_text: str) -> list[dict]:
    """
    Attempt to parse receipt text into structured line items.

    Looks for patterns like:
        ITEM NAME            123.45
        ITEM NAME     2 x    50.00

    Returns a list of dicts with 'description' and 'price' keys.
    """
    lines = raw_text.strip().split("\n")
    items = []

    # Pattern: text followed by a price (number with optional decimal)
    price_pattern = re.compile(
        r"^(.+?)\s+([\d,]+\.?\d{0,2})\s*$"
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = price_pattern.match(line)
        if match:
            description = match.group(1).strip()
            price_str = match.group(2).replace(",", "")

            # Skip lines that look like totals, tax, etc.
            skip_keywords = [
                "total", "subtotal", "sub total", "tax", "vat",
                "change", "cash", "tender", "discount", "amount due",
                "balance", "payment",
            ]
            if any(kw in description.lower() for kw in skip_keywords):
                continue

            try:
                price = float(price_str)
                if 0 < price < 100000:  # Reasonable price range
                    items.append({
                        "description": description,
                        "price": price,
                    })
            except ValueError:
                continue

    return items
