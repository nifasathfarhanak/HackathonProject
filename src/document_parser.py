
import pypdf
import docx
import xml.etree.ElementTree as ET
import markdown
import io

def parse_document(file_path: str, file_content: bytes) -> str:
    """
    Parses the content of an uploaded file based on its extension.

    Args:
        file_path: The full path or name of the file.
        file_content: The raw byte content of the file.

    Returns:
        The extracted text content as a string.
    """
    file_ext = file_path.lower().split('.')[-1]

    if file_ext == "pdf":
        text = ""
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            return f"Error parsing PDF: {e}"

    elif file_ext == "docx":
        try:
            document = docx.Document(io.BytesIO(file_content))
            return "\n".join([para.text for para in document.paragraphs])
        except Exception as e:
            return f"Error parsing DOCX: {e}"

    elif file_ext == "xml":
        try:
            # We decode the bytes to a string for the XML parser
            xml_string = file_content.decode("utf-8")
            root = ET.fromstring(xml_string)
            # Iterate through all elements and join their text content
            return "\n".join(filter(None, [elem.text for elem in root.iter()]))
        except Exception as e:
            return f"Error parsing XML: {e}"

    elif file_ext in ["md", "markdown", "txt"]:
        # For Markdown and plain text, the raw text is best for the LLM
        return file_content.decode("utf-8")

    else:
        raise ValueError(f"Unsupported file type: {file_ext}")

