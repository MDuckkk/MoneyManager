# -*- coding: utf-8 -*-
"""Phục hồi dấu tiếng Việt cho field text — ĐÃ TẮT (bản không-LLM).

Trước đây dùng Gemini (qua service_account) để thêm dấu cho field text. Deploy keyless
không có LLM, nên các hàm ở đây là identity (giữ nguyên text). Giữ nguyên chữ ký để
`common.build_record` gọi mà không phải đổi gì.
"""


def set_backend(fn=None) -> None:      # tương thích ngược — không dùng nữa
    return None


def restore(text):
    return text


def restore_fields(fields: dict, names):
    """Không đổi text; trả (fields_copy, {}) — không trường nào bị thay -> không có bản gốc."""
    return dict(fields), {}


def restore_listfield(value, keys=("ten_hang", "dvt")):
    return value
