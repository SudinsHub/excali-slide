from pathlib import Path

from app.errors import BadRequestError


def detect_resource_kind(filename: str, header_bytes: bytes) -> tuple[str, str]:
    """Detect resource kind and mime type based on extension and magic bytes.

    Returns (kind, mime). Raises BadRequestError if unsupported or invalid.
    Kinds: pdf | docx | pptx | md | txt | image
    """
    ext = Path(filename).suffix.lower()

    # 1. PDF
    if ext == ".pdf":
        if header_bytes.startswith(b"%PDF"):
            return "pdf", "application/pdf"
        raise BadRequestError(
            code="invalid_file_format",
            message=f"File '{filename}' has .pdf extension but does not match PDF magic bytes",
        )

    # 2. DOCX & PPTX (ZIP container)
    if ext in (".docx", ".pptx"):
        if header_bytes.startswith(b"PK\x03\x04") or header_bytes.startswith(b"PK\x05\x06"):
            if ext == ".docx":
                return (
                    "docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            return (
                "pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
        raise BadRequestError(
            code="invalid_file_format",
            message=f"File '{filename}' has {ext} extension but does not match Zip/Office magic bytes",
        )

    # 3. Markdown / Plain Text
    if ext in (".md", ".markdown"):
        return "md", "text/markdown"
    if ext in (".txt", ".text"):
        return "text", "text/plain"

    # 4. Images
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        if header_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image", "image/png"
        if header_bytes.startswith(b"\xff\xd8\xff"):
            return "image", "image/jpeg"
        if header_bytes.startswith(b"RIFF") and b"WEBP" in header_bytes[:16]:
            return "image", "image/webp"
        if header_bytes.startswith(b"GIF87a") or header_bytes.startswith(b"GIF89a"):
            return "image", "image/gif"
        raise BadRequestError(
            code="invalid_file_format",
            message=f"File '{filename}' has image extension {ext} but does not match valid image magic bytes",
        )

    raise BadRequestError(
        code="unsupported_file_type",
        message=f"Unsupported file format '{ext}' for file '{filename}'. Supported types: PDF, DOCX, PPTX, MD, TXT, PNG, JPEG, WEBP",
    )
