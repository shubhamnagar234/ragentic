import httpx
from typing import List
from app.services.ingestion.chunker import Chunk, chunk_text_hierarchical
from app.config import settings

# File extensions to ingest
ALLOWED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".go", ".rs", ".java", ".cpp", ".c",
    ".md", ".txt", ".json", ".yaml", ".yml",
}

# Paths to skip
SKIP_PATHS = {
    "node_modules", ".git", "dist", "build",
    "__pycache__", ".venv", "venv", "env",
    "package-lock.json", "yarn.lock", "poetry.lock",
    "uv.lock", ".pytest_cache",
}


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Parses a GitHub URL into (owner, repo).
    Example: https://github.com/vercel/next.js → ("vercel", "next.js")
    """
    url = url.rstrip("/")
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return parts[0], parts[1]


async def fetch_repo_tree(owner: str, repo: str) -> List[dict]:
    """
    Fetches the full file tree of a GitHub repo using the GitHub API.
    Returns list of file objects with path and download_url.
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    files = [
        item for item in data.get("tree", [])
        if item["type"] == "blob"
    ]

    print(f"[github_ingestor] Found {len(files)} files in {owner}/{repo}")
    return files


def should_ingest_file(path: str) -> bool:
    """
    Returns True if the file should be ingested based on
    extension and path filters.
    """
    from pathlib import Path

    path_obj = Path(path)

    # Check if any part of path is in skip list
    for part in path_obj.parts:
        if part in SKIP_PATHS:
            return False

    # Check extension
    return path_obj.suffix.lower() in ALLOWED_EXTENSIONS


async def fetch_file_content(download_url: str) -> str:
    """
    Fetches the raw content of a single file from GitHub.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(download_url, timeout=10.0)
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(f"[github_ingestor] Failed to fetch file: {e}")
        return ""


async def ingest_github(url: str, source_id: str) -> tuple[List[Chunk], str]:
    """
    Full GitHub repo ingestion pipeline:
    1. Parse URL → owner/repo
    2. Fetch file tree via GitHub API
    3. Filter files by extension and path
    4. Fetch and chunk each file
    Returns (chunks, title)
    """
    print(f"[github_ingestor] Starting GitHub ingestion: {url}")

    owner, repo = parse_github_url(url)
    title = f"{owner}/{repo}"

    # Fetch file tree
    all_files = await fetch_repo_tree(owner, repo)

    # Filter to allowed files
    files_to_ingest = [
        f for f in all_files
        if should_ingest_file(f["path"])
    ]

    print(f"[github_ingestor] Ingesting {len(files_to_ingest)} files from {title}")

    all_chunks = []

    for file in files_to_ingest:
        path = file["path"]
        download_url = file.get("url", "")

        # Fetch raw content via GitHub API
        headers = {"Accept": "application/vnd.github.v3.raw"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code != 200:
                    continue
                content = response.text
        except Exception as e:
            print(f"[github_ingestor] Skipping {path}: {e}")
            continue

        if not content.strip():
            continue

        # Prefix content with file path for context
        full_text = f"# File: {path}\n\n{content}"

        # Chunk the file
        chunks = chunk_text_hierarchical(full_text)

        # Tag with metadata
        for chunk in chunks:
            chunk.metadata["source_id"] = source_id
            chunk.metadata["file_path"] = path
            chunk.metadata["repo"] = title
            chunk.metadata["is_code"] = True

        all_chunks.extend(chunks)

    print(f"[github_ingestor] Created {len(all_chunks)} chunks from {title}")
    return all_chunks, title