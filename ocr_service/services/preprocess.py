# -*- coding: utf-8 -*-
"""
Tiền xử lý ảnh trang trước OCR (ảnh chụp nghiêng/chụp màn hình): deskew + tăng nét ảnh.

Cắm trong run.predict_page NGAY SAU render ảnh, TRƯỚC PP-StructureV3 -> dòng nằm ngang,
reading-order + dựng bảng đỡ lệch. `preprocess_page` là API cho pipeline (degrade nếu thiếu
lib jdeskew / lỗi -> trả ảnh gốc). Tắt cả tầng: OCR_PREPROCESS=0. Bỏ riêng deskew:
PDF_PREPROCESS_SKIP_DESKEW=true.

`enhance_image`: CLAHE (kênh L của LAB -> GIỮ MÀU) + bilateral khử nhiễu giữ cạnh chữ.
Giúp ảnh CHỤP/SCAN ánh sáng lệch/nhiễu; gần như vô hại với PDF digital-born nên MẶC ĐỊNH TẮT,
bật bằng OCR_IMG_ENHANCE=1 (hoặc toggle per-request "img_enhance"). Tham số chỉnh qua env:
OCR_CLAHE_CLIP (2.0), OCR_CLAHE_TILE (8), OCR_BILATERAL_D (7), OCR_BILATERAL_SIGMA (50).

Kèm vài tiện ích (deskew_image / preprocess_image_cv2 / is_blank_page) dùng khi cần.
"""
import logging
import os

from PIL import Image

log = logging.getLogger("ocr.preprocess")


def deskew_image(image, angle_max: float = 45.0, return_angle: bool = False):
    """Deskew image (np array) và (tuỳ chọn) trả về góc xoay. Cần jdeskew."""
    from jdeskew.estimator import get_angle
    from jdeskew.utility import rotate
    angle = get_angle(image, angle_max=angle_max)
    rotated_np = image
    if angle != 0:
        rotated_np = rotate(image, angle)
    if return_angle:
        return rotated_np, angle
    return rotated_np


def preprocess_image_pil(image: Image.Image, return_rgb: bool = False):
    """Tiền xử lý ảnh trang cho OCR. return_rgb=True -> trả thêm ảnh RGB đã qua cùng phép
    biến đổi (giữ màu). PDF_PREPROCESS_SKIP_DESKEW=true -> bỏ deskew (PDF digital-born)."""
    import cv2
    import numpy as np
    from jdeskew.utility import rotate

    rgb = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    skip_deskew = os.getenv("PDF_PREPROCESS_SKIP_DESKEW", "false").lower() == "true"

    if return_rgb:
        if not skip_deskew:
            gray, angle = deskew_image(gray, return_angle=True)
            if angle != 0:
                rgb = rotate(rgb, angle)
    else:
        if not skip_deskew:
            gray = deskew_image(gray)

    gray_img = Image.fromarray(gray, mode="L")
    if not return_rgb:
        return gray_img
    return gray_img, Image.fromarray(rgb, mode="RGB")


def deskew_pil(image: Image.Image):
    """Deskew 1 ảnh PIL lẻ (vd CROP vùng BẢNG) bằng jdeskew, giữ RGB.
    Crop bảng thường nghiêng ĐỀU hơn cả trang -> 1 góc xoay nắn tốt, vision đọc bảng đỡ lệch.
    Trả (ảnh_đã_xoay, góc°). Thiếu jdeskew / lỗi -> (ảnh gốc, 0.0) (tự degrade)."""
    try:
        import cv2
        import numpy as np
        from jdeskew.utility import rotate
        rgb = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        _, angle = deskew_image(gray, return_angle=True)
        if angle:
            rgb = rotate(rgb, angle)
        return Image.fromarray(rgb), float(angle)
    except Exception as e:
        log.warning("deskew crop bỏ qua (%s) -> ảnh gốc", type(e).__name__)
        return image, 0.0


def enhance_image(image: Image.Image) -> Image.Image:
    """Tăng tương phản + khử nhiễu cho ảnh CHỤP/SCAN, GIỮ NGUYÊN MÀU (cho logo/dấu đỏ).

    CLAHE trên kênh L của LAB (không đụng a/b -> màu nguyên vẹn) + bilateralFilter màu
    (khử nhiễu nhưng giữ cạnh chữ). Tham số đọc từ env (mặc định bộ đã chốt qua thực nghiệm).
    Trả ảnh RGB. KHÔNG nhị phân (Surya/Paddle train trên ảnh xám/màu, nhị phân làm giảm acc)."""
    import cv2
    import numpy as np

    clip = float(os.getenv("OCR_CLAHE_CLIP", "2.0"))
    tile = int(os.getenv("OCR_CLAHE_TILE", "8"))
    d = int(os.getenv("OCR_BILATERAL_D", "7"))
    sigma = float(os.getenv("OCR_BILATERAL_SIGMA", "50"))

    rgb = np.array(image.convert("RGB"))
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile)).apply(l)
    rgb = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)
    rgb = cv2.bilateralFilter(rgb, d, sigma, sigma)
    return Image.fromarray(rgb, mode="RGB")


def preprocess_image_cv2(image, return_bgr: bool = True):
    """Tiền xử lý ảnh BGR (cho YOLO/layout/detector OpenCV): gray -> trả BGR 3 kênh."""
    import cv2
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def is_blank_page(image, white_thresh: int = 250, blank_ratio: float = 0.998) -> bool:
    """Trang trắng? Dựa trên tỷ lệ điểm ảnh trắng + Canny edge."""
    import cv2
    import numpy as np

    if image is None or getattr(image, "size", 0) == 0:
        return True
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.shape[2] == 3 else image
    else:
        gray = image

    ratio = np.count_nonzero(gray >= white_thresh) / gray.size
    if ratio < blank_ratio:
        return False
    edges = cv2.Canny(gray, 50, 150)
    return bool(np.count_nonzero(edges) < (gray.size * 0.00001))


# --- API cho pipeline ---

def preprocess_page(image: Image.Image) -> Image.Image:
    """Tiền xử lý ảnh trang (giữ RGB) cho pipeline. OCR_PREPROCESS=0 -> bỏ qua cả tầng.

    Bước 1 deskew (mặc định BẬT; bỏ riêng bằng PDF_PREPROCESS_SKIP_DESKEW=true).
    Bước 2 enhance ảnh CLAHE+denoise (mặc định TẮT; bật bằng OCR_IMG_ENHANCE=1 hoặc
    toggle per-request "img_enhance" — nên bật cho ảnh chụp/scan, để tắt cho PDF digital-born).
    Mỗi bước tự degrade về ảnh trước đó nếu thiếu lib / lỗi (không vỡ pipeline)."""
    from options import flag
    if not flag("preprocess", "OCR_PREPROCESS", True):
        return image
    try:
        _, color = preprocess_image_pil(image, return_rgb=True)
    except Exception as e:
        log.warning("deskew bỏ qua (%s) -> ảnh gốc", type(e).__name__)
        color = image
    if flag("img_enhance", "OCR_IMG_ENHANCE", False):
        try:
            color = enhance_image(color)
        except Exception as e:
            log.warning("enhance ảnh bỏ qua (%s) -> ảnh trước đó", type(e).__name__)
    return color
