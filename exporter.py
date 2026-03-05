from reportlab.pdfgen import canvas
from docx import Document
import json
import os

class Exporter:
    @staticmethod
    async def to_txt(text: str, filename: str):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)
        return filename

    @staticmethod
    async def to_pdf(text: str, filename: str):
        c = canvas.Canvas(filename)
        # Simple PDF generation logic
        # In production, we'd handle RTL for Arabic and multi-page
        c.drawString(100, 750, text[:100]) # Placeholder
        c.save()
        return filename

    @staticmethod
    async def to_docx(text: str, filename: str):
        doc = Document()
        doc.add_paragraph(text)
        doc.save(filename)
        return filename

    @staticmethod
    async def to_json(data: dict, filename: str):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return filename
