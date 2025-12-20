from app.core.graph_state import PDFChunk
from app.utils.embeddings import get_embedding, cosine_similarity
from app.utils.logging import get_logger

logger = get_logger(__name__)

ANCHOR_KEYWORDS = [
    "application information",
    "electrical characteristics",
    "typical application",
    "design procedure",
    "feedback",
    "compensation",
    "reference design",
]

ANCHOR_EMBEDDINGS_CACHE: dict[str, list[float]] = {}


async def _get_anchor_embeddings() -> list[list[float]]:
    if not ANCHOR_EMBEDDINGS_CACHE:
        for keyword in ANCHOR_KEYWORDS:
            embedding = await get_embedding(keyword)
            ANCHOR_EMBEDDINGS_CACHE[keyword] = embedding
    return list(ANCHOR_EMBEDDINGS_CACHE.values())


async def route_chunks(chunks: list[PDFChunk], similarity_threshold: float = 0.75) -> dict[str, list[PDFChunk]]:
    await logger.ainfo("semantic_routing_start", chunks_count=len(chunks))

    stage1_filtered = _heuristic_filter(chunks)
    await logger.ainfo("heuristic_filter_complete", filtered_count=len(stage1_filtered))

    stage2_filtered = await _embedding_filter(stage1_filtered, similarity_threshold)
    await logger.ainfo("embedding_filter_complete", filtered_count=len(stage2_filtered))

    categorized = _categorize_chunks(stage2_filtered)
    await logger.ainfo("chunk_categorization_complete", categories=list(categorized.keys()))

    return categorized


def _heuristic_filter(chunks: list[PDFChunk]) -> list[PDFChunk]:
    filtered: list[PDFChunk] = []
    keywords_lower = [kw.lower() for kw in ANCHOR_KEYWORDS]

    for chunk in chunks:
        content_lower = chunk.content.lower()
        section_lower = (chunk.section_title or "").lower()

        if any(keyword in content_lower or keyword in section_lower for keyword in keywords_lower):
            filtered.append(chunk)
        elif any(keyword in content_lower[:500] for keyword in ["table", "figure", "equation"]):
            filtered.append(chunk)

    return filtered


async def _embedding_filter(chunks: list[PDFChunk], threshold: float) -> list[PDFChunk]:
    if not chunks:
        return []

    anchor_embeddings = await _get_anchor_embeddings()
    filtered: list[PDFChunk] = []

    for chunk in chunks:
        chunk_embedding = await get_embedding(chunk.content[:1000])
        max_similarity = max(
            (cosine_similarity(chunk_embedding, anchor) for anchor in anchor_embeddings),
            default=0.0,
        )

        if max_similarity >= threshold:
            filtered.append(chunk)

    return filtered


def _categorize_chunks(chunks: list[PDFChunk]) -> dict[str, list[PDFChunk]]:
    categorized: dict[str, list[PDFChunk]] = {
        "tables": [],
        "prose": [],
        "figures": [],
    }

    for chunk in chunks:
        content_lower = chunk.content.lower()
        section_lower = (chunk.section_title or "").lower()

        if "table" in content_lower or "electrical characteristics" in section_lower:
            categorized["tables"].append(chunk)
        elif "figure" in content_lower or "schematic" in content_lower or "reference design" in section_lower:
            categorized["figures"].append(chunk)
        else:
            categorized["prose"].append(chunk)

    return categorized
