import os
import tempfile
from typing import List

from app.services.ingestion.chunker import Chunk, chunk_transcript_hierarchical


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
    1. Download audio via yt-dlp
    2. Transcribe with faster-whisper
    3. Hierarchical chunking by time window
    Returns (chunks, title)
    """
    print(f"[video_ingestor] Starting video ingestion: {url}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Download audio
        audio_path, title = download_audio(url, tmp_dir)

        # Transcribe
        segments = transcribe_audio(audio_path)

        if not segments:
            print(f"[video_ingestor] No segments transcribed")
            return [], title

        # Hierarchical chunking
        chunks = chunk_transcript_hierarchical(segments)

        # Tag chunks with metadata
        for chunk in chunks:
            chunk.metadata["source_id"] = source_id
            chunk.metadata["url"] = url

        print(f"[video_ingestor] Created {len(chunks)} chunks from video")
        return chunks, title