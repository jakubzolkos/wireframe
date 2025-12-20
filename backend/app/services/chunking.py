import re
from app.core.graph_state import PDFChunk
from app.utils.embeddings import get_embedding, cosine_similarity
from app.utils.logging import get_logger

logger = get_logger(__name__)

SENTENCE_END_PATTERN = re.compile(r"[.!?]\s+")
COSINE_DISTANCE_THRESHOLD = 0.3


async def semantic_chunk(text: str, page_number: int, section_title: str | None = None) -> list[PDFChunk]:
    await logger.ainfo("semantic_chunking_start", text_length=len(text), page=page_number)

    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return [PDFChunk(content=text, page_number=page_number, section_title=section_title)]

    chunks: list[PDFChunk] = []
    current_chunk_sentences: list[str] = []
    previous_embedding: list[float] | None = None

    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue

        current_embedding = await get_embedding(sentence)

        if previous_embedding is not None:
            distance = 1.0 - cosine_similarity(previous_embedding, current_embedding)

            if distance > COSINE_DISTANCE_THRESHOLD and current_chunk_sentences:
                chunk_text = " ".join(current_chunk_sentences)
                chunks.append(
                    PDFChunk(
                        content=chunk_text,
                        page_number=page_number,
                        section_title=section_title,
                    )
                )
                current_chunk_sentences = []

        current_chunk_sentences.append(sentence)
        previous_embedding = current_embedding

    if current_chunk_sentences:
        chunk_text = " ".join(current_chunk_sentences)
        chunks.append(
            PDFChunk(
                content=chunk_text,
                page_number=page_number,
                section_title=section_title,
            )
        )

    await logger.ainfo("semantic_chunking_complete", chunks_count=len(chunks))
    return chunks


def _split_sentences(text: str) -> list[str]:
    sentences = SENTENCE_END_PATTERN.split(text)
    return [s.strip() for s in sentences if s.strip()]
