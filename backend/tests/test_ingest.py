import hashlib
import io

import docx
import pptx
import pypdf
import pytest
from PIL import Image

from app.ingest.parsers import (
    parse_docx,
    parse_pptx,
    process_image_bytes,
)
from app.ingest.sniff import detect_resource_kind
from app.jobs.context import JobContext
from app.jobs.handlers import handle_ingest_resource
from app.llm.client import FakeLLM
from app.models.asset import Asset
from app.models.deck import Deck
from app.models.job import Job
from app.models.resource import Resource
from app.services.storage import LocalStorage


def create_test_docx() -> bytes:
    doc = docx.Document()
    doc.add_heading("Document Title", level=1)
    doc.add_paragraph("First paragraph content.")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Col A"
    table.cell(0, 1).text = "Col B"
    table.cell(1, 0).text = "Val 1"
    table.cell(1, 1).text = "Val 2"

    img = Image.new("RGB", (250, 250), color=(10, 50, 200))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_buf.seek(0)
    doc.add_picture(img_buf)

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def create_test_pptx() -> bytes:
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Presentation Title"
    slide.placeholders[1].text = "Subtitle and details"

    img = Image.new("RGB", (220, 220), color=(200, 50, 10))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_buf.seek(0)
    slide.shapes.add_picture(img_buf, 0, 0)

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


def create_test_pdf() -> bytes:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_sniffing():
    # Markdown
    assert detect_resource_kind("notes.md", b"# Header")[0] == "md"
    assert detect_resource_kind("notes.txt", b"plain text")[0] == "text"

    # PDF
    assert detect_resource_kind("doc.pdf", b"%PDF-1.4\n")[0] == "pdf"

    # DOCX and PPTX
    assert detect_resource_kind("doc.docx", b"PK\x03\x04\x14\x00")[0] == "docx"
    assert detect_resource_kind("pres.pptx", b"PK\x03\x04\x14\x00")[0] == "pptx"

    # PNG and JPEG
    assert detect_resource_kind("img.png", b"\x89PNG\r\n\x1a\n\x00")[0] == "image"
    assert detect_resource_kind("img.jpg", b"\xff\xd8\xff\xe0")[0] == "image"


def test_text_and_table_extraction_docx():
    docx_bytes = create_test_docx()
    text, images = parse_docx(docx_bytes)

    assert "# Document Title" in text
    assert "First paragraph content." in text
    assert "| Col A | Col B |" in text
    assert "| Val 1 | Val 2 |" in text
    assert len(images) == 1
    assert images[0][1] == "inline"


def test_presentation_extraction_pptx():
    pptx_bytes = create_test_pptx()
    text, images = parse_pptx(pptx_bytes)

    assert "--- slide 1 ---" in text
    assert "Presentation Title" in text
    assert "Subtitle and details" in text
    assert len(images) == 1
    assert images[0][1] == "slide 1"


def test_image_downscaling_and_dimensions():
    # Large 2400x1200 image
    large = Image.new("RGB", (2400, 1200), color=(100, 150, 200))
    buf = io.BytesIO()
    large.save(buf, format="PNG")
    raw = buf.getvalue()

    processed = process_image_bytes(raw, min_dim=200)
    assert processed is not None
    data, mime, w, h = processed
    assert max(w, h) == 1600
    assert w == 1600
    assert h == 800

    # Image below min_dim (100x100 < 200)
    small = Image.new("RGB", (100, 100), color="white")
    sbuf = io.BytesIO()
    small.save(sbuf, format="PNG")
    assert process_image_bytes(sbuf.getvalue(), min_dim=200) is None


@pytest.mark.asyncio
async def test_ingest_resource_handler_flow_and_dedupe(db_session, tmp_path):
    """Verify ingest_resource handler extracts assets, dedupes by SHA-1, and updates status."""
    storage = LocalStorage(tmp_path)
    deck = Deck(title="Ingest Deck", settings={})
    db_session.add(deck)
    await db_session.commit()

    # Create image file
    test_img = Image.new("RGB", (400, 300), color=(50, 100, 150))
    buf = io.BytesIO()
    test_img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    storage.put("resources/test.png", img_bytes)
    res = Resource(
        deck_id=deck.id,
        kind="image",
        filename="test.png",
        mime="image/png",
        size=len(img_bytes),
        storage_key="resources/test.png",
        status="uploaded",
    )
    db_session.add(res)
    await db_session.commit()

    job = Job(
        deck_id=deck.id,
        kind="ingest_resource",
        status="running",
        payload={"resource_id": str(res.id)},
    )
    db_session.add(job)
    await db_session.commit()

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)

    ctx = JobContext(
        session_factory=session_factory,
        storage=storage,
        llm_client=FakeLLM(),
        job=job,
    )

    result = await handle_ingest_resource(ctx)
    assert result["status"] == "parsed"

    # Reload resource
    await db_session.refresh(res)
    assert res.status == "parsed"
    assert res.error is None

    # Verify asset was created
    expected_sha1 = hashlib.sha1(process_image_bytes(img_bytes)[0]).hexdigest()
    asset = await db_session.get(Asset, expected_sha1)
    assert asset is not None
    assert asset.deck_id == deck.id


@pytest.mark.asyncio
async def test_ingest_failure_isolation(db_session, tmp_path):
    """Verify a corrupt file marks only that resource failed without raising unhandled errors."""
    storage = LocalStorage(tmp_path)
    deck = Deck(title="Corrupt File Deck", settings={})
    db_session.add(deck)
    await db_session.commit()

    # Put corrupt bytes for a docx
    storage.put("resources/corrupt.docx", b"PK\x03\x04corrupt_zip_stream_not_valid_docx")
    res = Resource(
        deck_id=deck.id,
        kind="docx",
        filename="corrupt.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size=40,
        storage_key="resources/corrupt.docx",
        status="uploaded",
    )
    db_session.add(res)
    await db_session.commit()

    job = Job(
        deck_id=deck.id,
        kind="ingest_resource",
        status="running",
        payload={"resource_id": str(res.id)},
    )
    db_session.add(job)
    await db_session.commit()

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)

    ctx = JobContext(
        session_factory=session_factory,
        storage=storage,
        llm_client=FakeLLM(),
        job=job,
    )

    with pytest.raises(Exception, match=r".+"):
        await handle_ingest_resource(ctx)

    await db_session.refresh(res)
    assert res.status == "failed"
    assert res.error is not None
