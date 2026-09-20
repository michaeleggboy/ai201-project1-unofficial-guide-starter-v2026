"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)")


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _oversized_split(
    text: str, source: str, index: int, chunk_size: int, overlap: int
) -> list[Chunk]:
    """A single paragraph too big to trust whole falls back to char windows."""
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        piece = text[start : start + chunk_size].strip()
        if piece:
            chunks.append(
                Chunk(
                    text=piece,
                    source=source,
                    index=index,
                    produced_by="chunker.py::split_documents",
                )
            )
            index += 1
        start += chunk_size - overlap
    return chunks


def _split_single_document(doc: Document, chunk_size: int, overlap: int) -> list[Chunk]:
    paragraphs = _paragraphs(doc.text)
    has_headers = any(_HEADER_RE.match(p) for p in paragraphs)

    # Short, unstructured documents (the campus_life case): no headers, and
    # the whole thing already fits in one chunk. Leave it alone rather than
    # slicing a three-sentence post into fragments.
    if not has_headers and len(doc.text) <= chunk_size:
        return [
            Chunk(
                text=doc.text.strip(),
                source=doc.source,
                index=0,
                produced_by="chunker.py::split_documents",
            )
        ]

    chunks: list[Chunk] = []
    index = 0
    header_stack: list[tuple[int, str]] = []

    for para in paragraphs:
        header_match = _HEADER_RE.match(para)
        if header_match:
            level = len(header_match.group(1))
            htext = header_match.group(2).strip()
            header_stack = [h for h in header_stack if h[0] < level]
            header_stack.append((level, htext))
            continue

        prefix = " — ".join(htext for _, htext in header_stack)
        full = f"{prefix}\n\n{para}" if prefix else para

        if len(full) <= chunk_size * 2:
            chunks.append(
                Chunk(
                    text=full.strip(),
                    source=doc.source,
                    index=index,
                    produced_by="chunker.py::split_documents",
                )
            )
            index += 1
        else:
            oversized = _oversized_split(full, doc.source, index, chunk_size, overlap)
            chunks.extend(oversized)
            index += len(oversized)

    return chunks or [
        Chunk(
            text=doc.text.strip(),
            source=doc.source,
            index=0,
            produced_by="chunker.py::split_documents",
        )
    ]


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    Split on markdown structure instead of a fixed character count.

      - A header line (#, ##, ###...) is never folded into a chunk's body;
        it becomes context, prepended to every chunk below it, so a fact
        never gets separated from the tier/section it belongs to. The full
        path is prepended ("Brightwater — When to go"), not just the nearest
        header: in a corpus of same-shaped guides the section names repeat
        across every document and only the title tells them apart.
      - Each paragraph becomes its own chunk. For a guide written as one
        `**Name**` paragraph per entry, that means each entry stays a
        single, self-contained chunk with its name and its facts together.
      - A short, unstructured document (no headers, already under
        chunk_size) is left as one chunk rather than split further — the
        "should one post stay one chunk" call from the docstring above,
        answered "yes" for short posts like campus_life's.
      - A paragraph that's unusually long on its own (more than double
        chunk_size) falls back to character-window splitting for just that
        paragraph, so no chunk balloons unbounded.
    """
    chunk_size = config.CHUNK_SIZE
    overlap = config.CHUNK_OVERLAP

    chunks: list[Chunk] = []
    for doc in documents:
        chunks.extend(_split_single_document(doc, chunk_size, overlap))
    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
