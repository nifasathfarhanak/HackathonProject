
import os
from pypdf import PdfReader
from docx import Document
import xml.etree.ElementTree as ET
import markdown

def parse_pdf(file_content):
    try:
        from io import BytesIO
        pdf_file = BytesIO(file_content)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error parsing PDF: {e}"

def parse_docx(file_content):
    try:
        from io import BytesIO
        doc_file = BytesIO(file_content)
        doc = Document(doc_file)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"Error parsing DOCX: {e}"

def parse_xml(file_content):
    try:
        root = ET.fromstring(file_content)
        # This is a simple traversal; might need to be adjusted for specific XML structures
        return ' '.join(elem.text for elem in root.iter() if elem.text)
    except Exception as e:
        return f"Error parsing XML: {e}"

def parse_markdown(file_content):
    try:
        return markdown.markdown(file_content.decode('utf-8'))
    except Exception as e:
        return f"Error parsing Markdown: {e}"

def parse_txt(file_content):
    try:
        return file_content.decode('utf-8')
    except Exception as e:
        return f"Error parsing TXT: {e}"


def parse_document(file_name, file_content):
    """Parses the content of an uploaded file based on its extension."""
    file_ext = os.path.splitext(file_name)[1].lower()

    if file_ext == '.pdf':
        return parse_pdf(file_content)
    elif file_ext == '.docx':
        return parse_docx(file_content)
    elif file_ext == '.xml':
        return parse_xml(file_content)
    elif file_ext in ['.md', '.markdown']:
        return parse_markdown(file_content)
    elif file_ext == '.txt':
        return parse_txt(file_content)
    else:
        return "Unsupported file type. Please upload a PDF, DOCX, XML, MD, or TXT file."
