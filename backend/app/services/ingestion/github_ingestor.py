import os
import shutil
import stat
import tempfile
import asyncio
from typing import List
from app.services.ingestion.chunker import Chunk, chunk_text_hierarchical

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


def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal (for Windows)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


async def ingest_github(url: str, source_id: str) -> tuple[List[Chunk], str]:
    """
    Full GitHub repo ingestion pipeline using git clone.
    Bypasses GitHub API rate limits.
    """
    print(f"[github_ingestor] Starting GitHub ingestion via git clone: {url}")

    owner, repo = parse_github_url(url)
    title = f"{owner}/{repo}"

    all_chunks = []
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        clone_url = f"https://github.com/{owner}/{repo}.git"
        
        # Clone repo asynchronously
        process = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", clone_url, temp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")
            
        print(f"[github_ingestor] Cloned {title} successfully.")

        # Walk directory
        for root, dirs, files in os.walk(temp_dir):
            # Modify dirs in-place to skip SKIP_PATHS
            dirs[:] = [d for d in dirs if d not in SKIP_PATHS]
            
            for file_name in files:
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, temp_dir)
                
                # Normalize slashes for consistency
                rel_path = rel_path.replace("\\", "/")
                
                if not should_ingest_file(rel_path):
                    continue
                    
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Skip binary files
                    continue
                except Exception as e:
                    print(f"[github_ingestor] Skipping {rel_path}: {e}")
                    continue
                    
                if not content.strip():
                    continue
                    
                # Prefix content with file path for context
                full_text = f"# File: {rel_path}\n\n{content}"
                
                # Chunk the file
                chunks = chunk_text_hierarchical(full_text)
                
                # Tag with metadata
                for chunk in chunks:
                    chunk.metadata["source_id"] = source_id
                    chunk.metadata["file_path"] = rel_path
                    chunk.metadata["repo"] = title
                    chunk.metadata["is_code"] = True
                    
                all_chunks.extend(chunks)
                
        print(f"[github_ingestor] Created {len(all_chunks)} chunks from {title}")
        
    finally:
        # Clean up temp directory, using onerror to handle Windows read-only files created by git
        try:
            shutil.rmtree(temp_dir, onerror=remove_readonly)
        except Exception as e:
            print(f"[github_ingestor] Failed to clean up temp dir {temp_dir}: {e}")

    return all_chunks, title