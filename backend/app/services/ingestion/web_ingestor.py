from typing import List
from app.services.ingestion.chunker import Chunk, chunk_text_hierarchical


async def fetch_web_content(url: str) -> tuple[str, str]:
    """
    Fetches and cleans web page content using crawl4ai.
    Returns (clean_text, title)
    """
    try:
        from crawl4ai import AsyncWebCrawler

        print(f"[web_ingestor] Crawling: {url}")

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)

            if not result.success:
                print(f"[web_ingestor] Failed to crawl: {url}")
                return "", ""

            # crawl4ai returns clean markdown
            clean_text = result.markdown or result.cleaned_html or ""
            title = result.metadata.get("title", url) if result.metadata else url

            print(f"[web_ingestor] Fetched {len(clean_text)} chars from: {title}")
            return clean_text, title

    except Exception as e:
        print(f"[web_ingestor] Error crawling {url}: {e}")
        return "", ""


async def ingest_web(url: str, source_id: str) -> tuple[List[Chunk], str]:
    """
    Full web ingestion pipeline:
    1. Fetch and clean content with crawl4ai
    2. Hierarchical chunking
    Returns (chunks, title)
    """
    print(f"[web_ingestor] Starting web ingestion: {url}")

    text, title = await fetch_web_content(url)

    if not text.strip():
        print(f"[web_ingestor] No content extracted from: {url}")
        return [], title

    # Hierarchical chunking
    chunks = chunk_text_hierarchical(text)

    # Tag chunks with metadata
    for chunk in chunks:
        chunk.metadata["source_id"] = source_id
        chunk.metadata["url"] = url

    print(f"[web_ingestor] Created {len(chunks)} chunks from web page")
    return chunks, title