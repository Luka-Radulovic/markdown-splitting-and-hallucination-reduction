from collections import Counter
import re 


def get_normal_font_size(page):
    font_sizes = []
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = span['size']
                font_sizes.append(size)
    if not font_sizes:
        return 10  # fallback

    # Find the most common font size (mode)
    counter = Counter(font_sizes)
    normal_size = counter.most_common(1)[0][0]
    return normal_size


def custom_header_detection(span, page=None, normal_font_size=10):
    text = span['text'].strip()
    font_size = span['size']
    bbox = span['bbox']
    page_height = page.rect.height if page else 1000

    font_flags = span.get('flags', 0)
    is_bold = (font_flags & 2) != 0
    is_italic = (font_flags & 1) != 0

    font_size_threshold = 1.2  # header font size must be 20% bigger than normal

    if not text:
        return ""

    if font_size < normal_font_size * font_size_threshold:
        return ""

    if not (is_bold or is_italic or text.isupper() or text.istitle()):
        return ""

    if len(text.split()) > 6:
        return ""

    if re.match(r"^\d+[\.\)]", text):
        return ""



    return "## "


def custom_hdr_info(span, page=None, normal_font_size = 10):
    return custom_header_detection(span, page, normal_font_size=normal_font_size)
