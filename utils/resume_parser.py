# utils/resume_parser.py - Extract text from PDF/DOCX files + file-structure checks
"""
Parses uploaded resume files (PDF, DOCX) and extracts text + metadata
for the ATS scanner.
"""
import io
import re


def parse_resume_file(uploaded_file) -> dict:
    """
    Parse an uploaded file (Streamlit UploadedFile) and return:
    {
        "text": extracted plain text,
        "file_type": "pdf" | "docx" | "txt",
        "file_checks": {
            "page_count": int,
            "has_images": bool,
            "has_tables": bool,
            "is_machine_readable": bool,
            "font_count": int,
            "issues": ["issue1", ...],
        }
    }
    """
    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)  # Reset for potential re-read
    
    if filename.endswith(".pdf"):
        return _parse_pdf(file_bytes)
    elif filename.endswith(".docx"):
        return _parse_docx(file_bytes)
    elif filename.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="replace")
        return {
            "text": text,
            "file_type": "txt",
            "file_checks": {
                "page_count": 1,
                "has_images": False,
                "has_tables": False,
                "is_machine_readable": True,
                "font_count": 0,
                "issues": [],
            }
        }
    else:
        return {
            "text": "",
            "file_type": "unknown",
            "file_checks": {
                "page_count": 0,
                "has_images": False,
                "has_tables": False,
                "is_machine_readable": False,
                "font_count": 0,
                "issues": ["Unsupported file format. Please upload a PDF, DOCX, or TXT file."],
            }
        }


def _parse_pdf(file_bytes: bytes) -> dict:
    """Extract text and metadata from a PDF file."""
    from PyPDF2 import PdfReader
    
    issues = []
    page_count = 0
    has_images = False
    font_names = set()
    all_text = []
    
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        page_count = len(reader.pages)
        
        # Check page count
        if page_count > 3:
            issues.append(f"Resume is {page_count} pages — most ATS systems prefer 1-2 pages")
        
        for page_num, page in enumerate(reader.pages):
            # Extract text
            page_text = page.extract_text() or ""
            all_text.append(page_text)
            
            # Check for images (embedded XObjects)
            if "/XObject" in (page.get("/Resources") or {}):
                xobjects = page["/Resources"]["/XObject"]
                if xobjects:
                    for obj_name in xobjects:
                        xobj = xobjects[obj_name]
                        if hasattr(xobj, "get") and xobj.get("/Subtype") == "/Image":
                            has_images = True
            
            # Extract font info
            if "/Font" in (page.get("/Resources") or {}):
                fonts = page["/Resources"]["/Font"]
                if fonts:
                    for font_name in fonts:
                        font_obj = fonts[font_name]
                        if hasattr(font_obj, "get"):
                            base_font = font_obj.get("/BaseFont", "")
                            if base_font:
                                font_names.add(str(base_font))
        
        combined_text = "\n".join(all_text).strip()
        
        # Check if PDF is machine-readable
        is_readable = len(combined_text.split()) > 20
        if not is_readable:
            issues.append("PDF appears to be image-based or scanned — ATS cannot read this! Convert to a text-based PDF.")
        
        # Check for images
        if has_images:
            issues.append("PDF contains embedded images — some ATS systems cannot process images")
        
        # Check font count (too many fonts = formatting complexity)
        if len(font_names) > 6:
            issues.append(f"PDF uses {len(font_names)} different fonts — keep it to 2-3 for ATS compatibility")
        
        # Check for non-standard fonts
        standard_fonts = {"arial", "helvetica", "times", "calibri", "cambria", "garamond", "georgia", "verdana", "courier"}
        non_standard = []
        for font in font_names:
            font_clean = str(font).replace("/", "").lower()
            # Strip common suffixes
            for suffix in ["-bold", "-italic", "-bolditalic", "-regular", "mt", ",bold", ",italic"]:
                font_clean = font_clean.replace(suffix, "")
            if font_clean and not any(std in font_clean for std in standard_fonts):
                non_standard.append(str(font).replace("/", ""))
        
        if non_standard and len(non_standard) > 2:
            issues.append(f"Non-standard fonts detected: {', '.join(non_standard[:3])} — may not render in some ATS")
        
        return {
            "text": combined_text,
            "file_type": "pdf",
            "file_checks": {
                "page_count": page_count,
                "has_images": has_images,
                "has_tables": False,  # PyPDF2 can't reliably detect tables
                "is_machine_readable": is_readable,
                "font_count": len(font_names),
                "issues": issues,
            }
        }
        
    except Exception as e:
        return {
            "text": "",
            "file_type": "pdf",
            "file_checks": {
                "page_count": 0,
                "has_images": False,
                "has_tables": False,
                "is_machine_readable": False,
                "font_count": 0,
                "issues": [f"Failed to parse PDF: {str(e)}"],
            }
        }


def _parse_docx(file_bytes: bytes) -> dict:
    """Extract text and metadata from a DOCX file."""
    from docx import Document
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    
    issues = []
    has_images = False
    has_tables = False
    
    try:
        doc = Document(io.BytesIO(file_bytes))
        
        # Extract all paragraph text
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        
        # Check for tables
        if doc.tables:
            has_tables = True
            issues.append(f"Document contains {len(doc.tables)} table(s) — many ATS systems scramble table content")
        
        # Check for images
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                has_images = True
                break
        
        if has_images:
            issues.append("Document contains embedded images — ATS cannot read text inside images")
        
        # Check for text boxes (often used in fancy resume templates)
        # Text boxes are stored in separate XML parts and are often missed by ATS
        import xml.etree.ElementTree as ET
        body_xml = doc.element.xml
        if "w:txbxContent" in body_xml or "wps:txbx" in body_xml:
            issues.append("Document uses text boxes — content inside text boxes is often invisible to ATS")
        
        # Check for columns (multi-column layouts)
        if "w:cols" in body_xml and 'w:num="2"' in body_xml or 'w:num="3"' in body_xml:
            issues.append("Multi-column layout detected — ATS may read columns in wrong order")
        
        # Check section count via headers
        if doc.sections:
            for section in doc.sections:
                if section.header and section.header.paragraphs:
                    header_text = " ".join(p.text for p in section.header.paragraphs).strip()
                    if header_text:
                        issues.append("Document has header content — many ATS systems ignore headers/footers")
                        break
                if section.footer and section.footer.paragraphs:
                    footer_text = " ".join(p.text for p in section.footer.paragraphs).strip()
                    if footer_text:
                        issues.append("Document has footer content — many ATS systems ignore headers/footers")
                        break
        
        combined_text = "\n".join(paragraphs)
        is_readable = len(combined_text.split()) > 20
        
        if not is_readable:
            issues.append("Very little text extracted — document may use graphics/text boxes for content")
        
        # Estimate page count (~300 words per page)
        word_count = len(combined_text.split())
        estimated_pages = max(1, round(word_count / 300))
        if estimated_pages > 3:
            issues.append(f"Resume appears to be {estimated_pages}+ pages — most ATS prefer 1-2 pages")
        
        return {
            "text": combined_text,
            "file_type": "docx",
            "file_checks": {
                "page_count": estimated_pages,
                "has_images": has_images,
                "has_tables": has_tables,
                "is_machine_readable": is_readable,
                "font_count": 0,
                "issues": issues,
            }
        }
        
    except Exception as e:
        return {
            "text": "",
            "file_type": "docx",
            "file_checks": {
                "page_count": 0,
                "has_images": False,
                "has_tables": False,
                "is_machine_readable": False,
                "font_count": 0,
                "issues": [f"Failed to parse DOCX: {str(e)}"],
            }
        }
