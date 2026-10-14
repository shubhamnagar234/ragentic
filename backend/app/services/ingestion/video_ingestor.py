import os
import re
import tempfile
from typing import List, Optional

from app.services.ingestion.chunker import Chunk, chunk_transcript_hierarchical


def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/|shorts\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_title(url: str) -> str:
    """Fetch video title using YouTube official oEmbed API (instant, never blocked)."""
    import urllib.request
    import json
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return data.get("title", "YouTube Video")
    except Exception as e:
        print(f"[video_ingestor] Failed to fetch oEmbed title: {e}")
        return "YouTube Video"


def parse_srt_timestamp(ts: str) -> float:
    """Convert SRT timestamp (HH:MM:SS,mmm or MM:SS,mmm) to seconds."""
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    return 0.0


def parse_srt(content: str) -> List[dict]:
    """Parse SRT content into list of segments [{text, start, end}]."""
    pattern = re.compile(r'(\d+:\d+:[\d\.,]+|\d+:[\d\.,]+)\s*-->\s*(\d+:\d+:[\d\.,]+|\d+:[\d\.,]+)')
    blocks = content.replace("\r\n", "\n").strip().split("\n\n")
    segments = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        ts_idx = -1
        for i, line in enumerate(lines):
            if "-->" in line:
                ts_idx = i
                break
        if ts_idx == -1:
            continue
        ts_match = pattern.search(lines[ts_idx])
        if not ts_match:
            continue
        start = parse_srt_timestamp(ts_match.group(1))
        end = parse_srt_timestamp(ts_match.group(2))
        text_lines = lines[ts_idx + 1:]
        text = " ".join(text_lines).strip()
        if text:
            segments.append({"text": text, "start": start, "end": end})
    return segments


def fetch_youtube_subtitles_ytdlp(url: str) -> List[dict]:
    """
    Fetches YouTube subtitles directly via yt-dlp using Android/iOS client emulation.
    Bypasses IP rate-limits and bot verification (Sign in to confirm you're not a bot).
    Completes in ~1-2 seconds.
    """
    import glob
    import yt_dlp

    print(f"[video_ingestor] Attempting subtitle extraction via yt-dlp mobile client: {url}")
    with tempfile.TemporaryDirectory() as tmp_dir:
        sub_prefix = os.path.join(tmp_dir, "sub")
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en.*"],
            "subtitlesformat": "srt",
            "outtmpl": sub_prefix,
            "extractor_args": {"youtube": {"player_client": ["android", "ios"]}},
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            srt_files = glob.glob(os.path.join(tmp_dir, "*.srt"))
            if not srt_files:
                print(f"[video_ingestor] No SRT subtitles found via yt-dlp")
                return []

            with open(srt_files[0], "r", encoding="utf-8") as f:
                content = f.read()

            segments = parse_srt(content)
            print(f"[video_ingestor] Extracted {len(segments)} subtitle segments via yt-dlp")
            return segments
        except Exception as e:
            print(f"[video_ingestor] yt-dlp subtitle extraction failed: {e}")
            return []


def fetch_youtube_transcript(video_id: str) -> List[dict]:
    """
    Fetches transcript segments using youtube-transcript-api.
    Used as secondary fallback for YouTube.
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    try:
        try:
            api = YouTubeTranscriptApi()
            transcript_data = api.fetch(video_id)
            snippets = getattr(transcript_data, "snippets", transcript_data)
        except (TypeError, AttributeError):
            snippets = YouTubeTranscriptApi.get_transcript(video_id)

        segments = []
        for s in snippets:
            if hasattr(s, "text"):
                text = s.text.strip()
                start = getattr(s, "start", 0.0)
                duration = getattr(s, "duration", 0.0)
            elif isinstance(s, dict):
                text = s.get("text", "").strip()
                start = s.get("start", 0.0)
                duration = s.get("duration", 0.0)
            else:
                continue

            if text:
                segments.append({
                    "text": text,
                    "start": float(start),
                    "end": float(start + duration),
                })
        return segments
    except Exception as e:
        print(f"[video_ingestor] youtube-transcript-api failed for {video_id}: {e}")
        return []


def download_audio(url: str, output_dir: str) -> str:
    """
    Downloads audio from YouTube, Shorts, or Loom using yt-dlp.
    Returns path to downloaded audio file.
    """
    import yt_dlp

    output_path = os.path.join(output_dir, "audio.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "extractor_args": {"youtube": {"player_client": ["android", "ios"]}},
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "Unknown")
        print(f"[video_ingestor] Downloaded: {title}")

    audio_file = os.path.join(output_dir, "audio.mp3")
    return audio_file, title


def transcribe_audio(audio_path: str) -> List[dict]:
    """
    Transcribes audio using faster-whisper.
    Returns list of segments: [{text, start, end}]
    """
    from faster_whisper import WhisperModel

    print(f"[video_ingestor] Loading Whisper model...")
    model = WhisperModel("base", device="cpu", compute_type="int8")

    print(f"[video_ingestor] Transcribing: {audio_path}")
    segments, info = model.transcribe(audio_path, beam_size=5)

    print(f"[video_ingestor] Detected language: {info.language}")

    result = []
    for segment in segments:
        result.append({
            "text": segment.text.strip(),
            "start": segment.start,
            "end": segment.end,
        })

    print(f"[video_ingestor] Transcribed {len(result)} segments")
    return result


async def ingest_video(url: str, source_id: str) -> tuple[List[Chunk], str]:
    """
    Full video/audio ingestion pipeline:
    1. Fast yt-dlp mobile client subtitle extraction (bypass IP & bot blocks).
    2. Fallback to youtube-transcript-api.
    3. Fallback to audio download via yt-dlp + faster-whisper.
    4. Hierarchical chunking by time window.
    Returns (chunks, title)
    """
    print(f"[video_ingestor] Starting video ingestion: {url}")
    title = get_video_title(url)
    segments = []

    # 1. Primary: yt-dlp mobile client subtitles (unblocked, ~1-2s)
    segments = fetch_youtube_subtitles_ytdlp(url)

    # 2. Secondary fallback: youtube-transcript-api
    if not segments:
        video_id = extract_youtube_video_id(url)
        if video_id:
            print(f"[video_ingestor] Subtitles not found via yt-dlp; trying youtube-transcript-api for: {video_id}")
            segments = fetch_youtube_transcript(video_id)

    # 3. Last fallback: yt-dlp audio download + whisper (for Loom or videos without subtitles)
    if not segments:
        print(f"[video_ingestor] No subtitles available; falling back to audio download + whisper")
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                audio_path, extracted_title = download_audio(url, tmp_dir)
                if not title or title == "YouTube Video":
                    title = extracted_title
                segments = transcribe_audio(audio_path)
            except Exception as e:
                print(f"[video_ingestor] Fallback download/transcribe failed: {e}")

    if not segments:
        print(f"[video_ingestor] No segments available for video")
        return [], title

    # Hierarchical chunking
    chunks = chunk_transcript_hierarchical(segments)

    # Tag chunks with metadata
    for chunk in chunks:
        chunk.metadata["source_id"] = source_id
        chunk.metadata["url"] = url
        chunk.metadata["title"] = title

    print(f"[video_ingestor] Created {len(chunks)} chunks from video '{title}'")
    return chunks, title