from openai import AsyncOpenAI
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    try:
        response = await client.embeddings.create(model=model, input=text)
        return response.data[0].embedding
    except Exception as e:
        await logger.aerror("embedding_error", error=str(e), text_length=len(text))
        raise


async def cosine_similarity(embedding1: list[float], embedding2: list[float]) -> float:
    import numpy as np

    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
