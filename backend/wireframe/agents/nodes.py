from io import BytesIO
import logging

from .state import WorkflowState
from wireframe.services.parser import DoclingService
from wireframe.services.llm import LLMService
from wireframe.services.storage import LocalStorageService

logger = logging.getLogger(__name__)

docling_svc = DoclingService()
llm_svc = LLMService()
storage_svc = LocalStorageService(base_root="./data") 

async def parse_node(state: WorkflowState) -> dict:
    logger.info("Parsing document...")
    doc = docling_svc.parse_pdf(state["file_path"])
    
    candidates = []
    for idx, picture in enumerate(doc.pictures):
        try:
            image = picture.get_image(doc)
            buffered = BytesIO()
            image.save(buffered, format="PNG") 
            candidates.append({
                "id": f"img_{idx}",
                "image": buffered.getvalue(),
                "context": {}
            })
        except Exception as e:
            logger.warning(f"Failed to process image {idx}: {e}")
            continue
    
    logger.info(f"Found {len(candidates)} images to process")
    return {
        "doc_object": doc,
        "raw_images": candidates
    }

async def classify_node(state: WorkflowState) -> dict:
    logger.info("Classifying images...")
    confirmed_schematics = await llm_svc.identify_schematics(state["raw_images"])
    return {"filtered_images": confirmed_schematics}

async def save_node(state: WorkflowState) -> dict:
    logger.info("Saving images...")
    # Use the local service to save to disk
    count = await storage_svc.save_filtered_images(
        job_id=state["job_id"],
        images=state["filtered_images"]
    )
    return {"saved_count": count}