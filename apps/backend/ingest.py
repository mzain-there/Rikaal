"""Dead-simple chunker. Good enough for MVP; swap for something smarter later."""


def chunk_text(text: str, max_chars: int = 1000, overlap: int = 150) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        # Try to break on a paragraph or sentence boundary near the end.
        slice_ = text[start:end]
        for sep in ("\n\n", "\n", ". "):
            idx = slice_.rfind(sep)
            if idx > max_chars * 0.5:
                end = start + idx + len(sep)
                break
        chunks.append(text[start:end].strip())

        if end >= len(text):
            break

        start = end - overlap

        # Move the start forward to the next word boundary.
        while start < len(text) and not text[start].isspace():
            start += 1
            
    return [c for c in chunks if c]
