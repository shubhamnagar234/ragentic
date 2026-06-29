import fitz  # PyMuPDF
from typing import List
from pathlib import Path

from app.services.ingestion.chunker import Chunk, chunk_text_hierarchical


def extract_pdf_pages(file_path: str) -> List[dict]:
    """
    Extracts text and detects image pages from a PDF.
    Returns list of {page_num, text, has_images}
    """
    doc = fitz.open(file_path)
    pages = []

    for page_num, page in enumerate(doc):
        text = page.get_text().strip()
        images = page.get_images(full=True)
        has_images = len(images) > 0

        pages.append({
            "page_num": page_num + 1,
            "text": text,
            "has_images": has_images,
        })

    doc.close()
    return pages


async def get_image_description(page_num: int, file_path: str) -> str:
    """
    Sends image-containing PDF pages to Gemini Vision for description.
    Returns text description of images/charts on that page.
    """
    try:
        import google.generativeai as genai
        from app.config import settings
        import fitz

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Render page as image
        doc = fitz.open(file_path)
        page = doc[page_num - 1]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        doc.close()

        # Send to Gemini Vision
        import PIL.Image
        import io
        image = PIL.Image.open(io.BytesIO(img_bytes))

        response = model.generate_content([
            "Describe all charts, graphs, diagrams, and images on this page. "
            "Be specific about data, labels, and visual information shown.",
            image,
        ])

        return response.text

    except Exception as e:
        print(f"[pdf_ingestor] Vision pass failed for page {page_num}: {e}")
        return ""


async def ingest_pdf(file_path: str, source_id: str) -> List[Chunk]:
    """
    Full PDF ingestion pipeline:
    1. Extract text from all pages
    2. Vision pass on image-containing pages
    3. Hierarchical chunking
    Returns list of Chunk objects ready for embedding.
    """
    print(f"[pdf_ingestor] Starting PDF ingestion: {file_path}")

    pages = extract_pdf_pages(file_path)
    all_chunks = []

    for page in pages:
        page_text = page["text"]

        # Vision pass for image pages
        if page["has_images"] and page_text:
            print(f"[pdf_ingestor] Running vision pass on page {page['page_num']}")
            image_description = await get_image_description(
                page["page_num"], file_path
            )
            if image_description:
                page_text += f"\n\n[Visual content on page {page['page_num']}]: {image_description}"

        if not page_text.strip():
            continue

        # Hierarchical chunking per page
        chunks = chunk_text_hierarchical(page_text)

        # Tag chunks with page number
        for chunk in chunks:
            chunk.page_num = page["page_num"]
            chunk.metadata["source_id"] = source_id
            chunk.metadata["page_num"] = page["page_num"]

        all_chunks.extend(chunks)

    print(f"[pdf_ingestor] Created {len(all_chunks)} chunks from PDF")
    return all_chunks