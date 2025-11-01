
import os
from pypdf import PdfReader
from docx import Document
import xml.etree.ElementTree as ET
import markdown

MAX_CHUNK_SIZE = 12000 # Define a max size for text chunks

def smart_chunk_text(text):
    """Splits text into chunks of a maximum size, respecting sentence boundaries."""
    chunks = []
    current_chunk = ""
    # Split by sentences to avoid breaking in the middle of a thought
    for sentence in text.split('. '):
        if len(current_chunk) + len(sentence) < MAX_CHUNK_SIZE:
            current_chunk += sentence + ". "
        else:
            # Add the completed chunk to the list
            chunks.append(current_chunk)
            # Start a new chunk
            current_chunk = sentence + ". "
    # Add the last remaining chunk
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def parse_pdf(file_content):
    try:
        from io import BytesIO
        pdf_file = BytesIO(file_content)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return smart_chunk_text(text)
    except Exception as e:
        return [f"Error parsing PDF: {e}"]

def parse_docx(file_content):
    try:
        from io import BytesIO
        doc_file = BytesIO(file_content)
        doc = Document(doc_file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return smart_chunk_text(text)
    except Exception as e:
        return [f"Error parsing DOCX: {e}"]

def parse_xml(file_content):
    try:
        root = ET.fromstring(file_content)
        text = ' '.join(elem.text for elem in root.iter() if elem.text)
        return smart_chunk_text(text)
    except Exception as e:
        return [f"Error parsing XML: {e}"]

def parse_markdown(file_content):
    try:
        text = markdown.markdown(file_content.decode('utf-8'))
        return smart_chunk_text(text)
    except Exception as e:
        return [f"Error parsing Markdown: {e}"]

def parse_txt(file_content):
    try:
        text = file_content.decode('utf-8')
        return smart_chunk_text(text)
    except Exception as e:
        return [f"Error parsing TXT: {e}"]


def parse_document(file_name, file_content):
    """Parses the content of an uploaded file and splits it into smart chunks."""
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
        return ["Unsupported file type. Please upload a PDF, DOCX, XML, MD, or TXT file."]
