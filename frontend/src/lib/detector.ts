export function detectSourceType(url: string): string {
  const lower = url.toLowerCase();

  if (lower.includes("youtube.com") || lower.includes("youtu.be")) {
    return "YOUTUBE";
  }
  if (lower.includes("loom.com")) {
    return "LOOM";
  }
  if (lower.includes("github.com")) {
    return "GITHUB";
  }
  if (lower.endsWith(".pdf")) {
    return "PDF";
  }
  if (lower.match(/\.(mp3|m4a|wav|ogg)$/)) {
    return "AUDIO";
  }
  if (lower.match(/\.(mp4|mov|avi|mkv|webm)$/)) {
    return "VIDEO";
  }
  if (lower.startsWith("http://") || lower.startsWith("https://")) {
    return "WEB";
  }

  return "UNKNOWN";
}
