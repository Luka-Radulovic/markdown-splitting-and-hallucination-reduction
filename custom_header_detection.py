import fitz  # pymupdf
from multi_column import column_boxes
import os
import re

def extract_text_and_tables(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""

    for page in doc:
        # Extract column text
        bboxes = column_boxes(page, footer_margin=50, no_image_text=True)
        for rect in bboxes:
            full_text += page.get_text(clip=rect, sort=True).strip() + "\n"

        # Extract tables (in markdown format)
        tables = page.find_tables(strategy="lines")
        if tables and len(tables.tables) > 0:
            for table in tables.tables:
                full_text += "\n" + table.to_markdown() + "\n"

    return full_text

def mark_sections(text):

    lines = text.splitlines() # HEURISTIC HEADER DETECTION 
    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Heuristic: title-cased or all caps, short, and not part of list
        if (
            stripped
            and not stripped.endswith(":")
            and len(stripped.split()) <= 10
            and (stripped.istitle() or stripped.isupper())
            and not re.match(r"^\d+[\.\)]", stripped)  # skip numbered points
            and i+1 < len(lines) and lines[i+1].strip() != "" # followed by text
        ):
            new_lines.append(f"## {stripped}")
        else:
            new_lines.append(line)

    return "\n".join(new_lines)
            
   # return text
