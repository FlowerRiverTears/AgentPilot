import unicodedata


def is_readable_text(text: str, min_length: int = 20) -> bool:
    normalized = " ".join(text.split())
    if len(normalized) < min_length:
        return False
    if "\x7f" in normalized:
        return False
    if looks_like_pdf_binary_text(normalized):
        return False

    chars = [char for char in normalized if not char.isspace()]
    if not chars:
        return False

    replacement_count = normalized.count("\ufffd")
    if replacement_count / len(chars) > 0.01:
        return False

    control_count = sum(1 for char in chars if unicodedata.category(char).startswith("C"))
    if control_count / len(chars) > 0.02:
        return False

    readable_count = sum(1 for char in chars if _is_readable_char(char))
    symbol_count = sum(1 for char in chars if unicodedata.category(char)[0] in {"S", "P"})
    letter_or_number_count = sum(1 for char in chars if char.isalnum())
    cjk_count = sum(1 for char in chars if _is_cjk(char))
    suspicious_extended_count = sum(1 for char in chars if _is_suspicious_extended(char))

    if readable_count / len(chars) < 0.7:
        return False
    if symbol_count / len(chars) > 0.45:
        return False
    if letter_or_number_count / len(chars) < 0.25:
        return False
    non_ascii_non_cjk_count = sum(1 for char in chars if ord(char) > 127 and not _is_cjk(char))
    cjk_ratio = cjk_count / len(chars)
    if suspicious_extended_count / len(chars) > 0.02 and cjk_ratio < 0.25:
        return False
    if non_ascii_non_cjk_count / len(chars) > 0.05 and cjk_ratio < 0.05:
        return False

    return True


def looks_like_pdf_binary_text(text: str) -> bool:
    markers = ("%PDF-", " endobj", " obj <", " endstream", " xref", "/FlateDecode", "/XRef")
    marker_count = sum(1 for marker in markers if marker in text)
    return marker_count >= 2 or (text.startswith("%PDF-") and "obj" in text)


def _is_readable_char(char: str) -> bool:
    category = unicodedata.category(char)
    if category[0] in {"L", "N", "P", "S"}:
        return True
    return char in "\n\r\t "


def _is_cjk(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x2A6DF
        or 0x2A700 <= codepoint <= 0x2B73F
        or 0x2B740 <= codepoint <= 0x2B81F
        or 0x2B820 <= codepoint <= 0x2CEAF
    )


def _is_suspicious_extended(char: str) -> bool:
    codepoint = ord(char)
    if codepoint < 128 or _is_cjk(char):
        return False
    if char in "，。！？；：（）【】《》、·℃±≤≥αβγμ":
        return False
    return codepoint <= 0x052F or 0x0590 <= codepoint <= 0x08FF
