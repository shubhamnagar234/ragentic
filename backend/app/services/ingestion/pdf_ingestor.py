import fitz  # PyMuPDF
from typing import List
from pathlib import Path
import asyncio

from app.services.ingestion.chunker import Chunk, chunk_text_hierarchical


def _has_significant_images(page, text: str) -> bool:
    """
    Determines if a page contains significant visual content (charts, diagrams, scans)
    rather than trivial icons, bullet points, headers, or decorative logos.
    """
    images = page.get_images(full=True)
    if not images:
        return False

    for img in images:
        try:
            w, h = img[2], img[3]
            # Significant images typically have at least 150px in both dimensions
            # and substantial pixel area (e.g. charts, graphs, flowcharts)
            if w >= 150 and h >= 150 and (w * h) >= 30000:
                return True
        except Exception:
            continue

    # If page has very little text but has images, it's likely an image-only slide or infographic
    if len(text.split()) < 25 and len(images) > 0:
        return True

    return False


def extract_pdf_pages(file_path: str) -> List[dict]:
    """
    Extracts text and detects image pages from a PDF.
    Returns list of {page_num, text, has_images}
    """
    doc = fitz.open(file_path)
    pages = []

    for page_num, page in enumerate(doc):
        text = page.get_text().strip()
        has_images = _has_significant_images(page, text)

        pages.append(
            {
                "page_num": page_num + 1,
                "text": text,
                "has_images": has_images,
            }
        )

    doc.close()
    return pages


def _describe_image_sync(page_num: int, file_path: str) -> str:
    try:
        from google import genai
        from app.config import settings
        import fitz
        import PIL.Image
        import io

        if not settings.GEMINI_API_KEY:
            return ""

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Render page as image
        doc = fitz.open(file_path)
        page = doc[page_num - 1]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        doc.close()

        image = PIL.Image.open(io.BytesIO(img_bytes))
        model_name = settings.LLM_VISION_MODEL or "gemini-2.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=[
                "Describe all charts, graphs, diagrams, and images on this page. "
                "Be specific about data, labels, and visual information shown.",
                image,
            ],
        )
        return response.text or ""
    except Exception as e:
        print(f"[pdf_ingestor] Vision pass failed for page {page_num}: {e}")
        return ""


async def get_image_description(
    page_num: int, file_path: str, sem: asyncio.Semaphore
) -> str:
    """
    Sends image-containing PDF pages to Gemini Vision for description using asyncio.to_thread
    and a concurrency-limiting semaphore.
    """
    async with sem:
        return await asyncio.to_thread(_describe_image_sync, page_num, file_path)


async def ingest_pdf(file_path: str, source_id: str) -> List[Chunk]:
    """
    Full PDF ingestion pipeline:
    1. Extract text from all pages
    2. Concurrent vision pass on pages with significant images (max 3 concurrent)
    3. Hierarchical chunking
    Returns list of Chunk objects ready for embedding.
    """
    print(f"[pdf_ingestor] Starting PDF ingestion: {file_path}")

    pages = extract_pdf_pages(file_path)
    all_chunks = []

    # Identify pages needing vision
    vision_pages = [p for p in pages if p["has_images"]]
    descriptions = {}
    if vision_pages:
        print(
            f"[pdf_ingestor] Found {len(vision_pages)} page(s) with visual content, running vision pass..."
        )
        sem = asyncio.Semaphore(3)
        tasks = [
            (
                p["page_num"],
                asyncio.create_task(
                    get_image_description(p["page_num"], file_path, sem)
                ),
            )
            for p in vision_pages
        ]
        for page_num, task in tasks:
            descriptions[page_num] = await task

    for page in pages:
        page_text = page["text"]
        image_desc = descriptions.get(page["page_num"])
        if image_desc:
            page_text += (
                f"\n\n[Visual content on page {page['page_num']}]: {image_desc}"
            )

        if not page_text.strip():
            continue

        chunks = chunk_text_hierarchical(page_text)
        for chunk in chunks:
            chunk.page_num = page["page_num"]
            chunk.metadata["source_id"] = source_id
            chunk.metadata["page_num"] = page["page_num"]

        all_chunks.extend(chunks)

    print(f"[pdf_ingestor] Created {len(all_chunks)} chunks from PDF")
    return all_chunks
