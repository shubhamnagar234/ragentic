import re
from enum import Enum


class SourceType(str, Enum):
    YOUTUBE = "YOUTUBE"
    LOOM = "LOOM"
    GITHUB = "GITHUB"
    WEB = "WEB"
    PDF = "PDF"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    UNKNOWN = "UNKNOWN"


def detect_source_type(url: str) -> SourceType:
    """
    Detects the source type from a given URL.
    Returns a SourceType enum value.
    """
    if not url:
        return SourceType.UNKNOWN

    url = url.strip().lower()

    # YouTube
    if any(domain in url for domain in ["youtube.com", "youtu.be"]):
        return SourceType.YOUTUBE

    # Loom
    if "loom.com" in url:
        return SourceType.LOOM

    # GitHub
    if "github.com" in url:
        return SourceType.GITHUB

    # Direct file URLs
    if url.endswith(".pdf"):
        return SourceType.PDF

    if url.endswith((".mp3", ".m4a", ".wav", ".ogg")):
        return SourceType.AUDIO

    if url.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
        return SourceType.VIDEO

    # Default to web URL
    if url.startswith(("http://", "https://")):
        return SourceType.WEB

    return SourceType.UNKNOWN


def get_source_label(source_type: SourceType) -> str:
    """
    Returns a human-readable label for a source type.
    Used in the frontend preview card.
    """
    labels = {
        SourceType.YOUTUBE: "YouTube video",
        SourceType.LOOM: "Loom recording",
        SourceType.GITHUB: "GitHub repository",
        SourceType.WEB: "Web page",
        SourceType.PDF: "PDF document",
        SourceType.AUDIO: "Audio file",
        SourceType.VIDEO: "Video file",
        SourceType.UNKNOWN: "Unknown source",
    }
    return labels.get(source_type, "Unknown source")