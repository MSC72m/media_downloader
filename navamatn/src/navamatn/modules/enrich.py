import re

from navamatn.core.models import EnrichmentResult, Transcript

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "your",
    "you",
    "are",
    "was",
    "were",
}


def enrich_transcript(transcript: Transcript) -> EnrichmentResult:
    words = re.findall(r"[a-zA-Z]{4,}", transcript.text.lower())

    counts: dict[str, int] = {}
    for word in words:
        if word in STOP_WORDS:
            continue
        counts[word] = counts.get(word, 0) + 1

    keywords = [word for word, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:8]]

    action_items = []
    for line in transcript.text.splitlines():
        normalized = line.strip()
        if normalized.lower().startswith(("todo", "action", "next")):
            action_items.append(normalized)

    return EnrichmentResult(keywords=keywords, action_items=action_items)
