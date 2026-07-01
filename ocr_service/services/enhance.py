# -*- coding: utf-8 -*-
"""Tầng enhance (vision đối chiếu field) — ĐÃ TẮT (bản không-LLM).

Trước đây đối chiếu field nguy hiểm với ảnh bằng Gemini vision. Deploy keyless không có
LLM, nên `maybe_enhance_record` trả record y nguyên. Giữ chữ ký để api/run gọi không đổi.
"""


def maybe_enhance_record(record: dict, pdf_path=None, page_idx: int = 0) -> dict:
    return record
