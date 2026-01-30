import logging
from io import BytesIO
from typing import cast
from docling_core.types.doc.document import SectionHeaderItem, PictureItem


from .state import WorkflowState, ImageCandidate, SaveResult, ExtractedCircuitDict
from wireframe.services.parser import DoclingService
from wireframe.services.llm import LLMService
from wireframe.services.storage import LocalStorageService
from wireframe.services.extractor import SchematicExtractionService

logger = logging.getLogger(__name__)

docling_svc = DoclingService()
llm_svc = LLMService()
storage_svc = LocalStorageService(base_root="./data")
extraction_svc = SchematicExtractionService()

async def parse_node(state: WorkflowState) -> WorkflowState:
    """Parses the PDF into a DoclingDocument object."""
    logger.info(f"Parsing document: {state.file_path}")
    doc = docling_svc.parse_pdf(state.file_path)
    
    # Return a new state object with the doc updated
    return state.model_copy(update={"doc_object": doc})

async def plan_node(state: WorkflowState) -> WorkflowState:
    """Extracts headers and asks LLM which sections are relevant."""
    doc = state.doc_object
    if not doc:
        logger.error("No document object found in state.")
        return state

    # Extract all section headers
    headers = set()
    for item, _ in doc.iterate_items():
        if isinstance(item, SectionHeaderItem):
            headers.add(item.text.strip())
            
    logger.info(f"Found {len(headers)} unique section headers.")
    
    # Ask LLM for relevant ones
    relevance_result = await llm_svc.identify_relevant_sections(list(headers))
    relevant_sections = relevance_result.relevant_section_headers
    
    logger.info(f"Identified {len(relevant_sections)} relevant sections: {relevant_sections}")
    
    return state.model_copy(update={"relevant_sections": relevant_sections})

async def extract_node(state: WorkflowState) -> WorkflowState:
    """
    Iterates through the document in reading order, tracking the current section,
    and extracts images only if they belong to a relevant section.
    """
    doc = state.doc_object
    relevant_sections = set(state.relevant_sections)
    candidates = []
    
    current_section = "Unknown"
    
    # Docling's iterate_items() yields (item, level) in reading order
    for item, _ in doc.iterate_items():
        
        # Track where we are in the document
        if isinstance(item, SectionHeaderItem):
            current_section = item.text.strip()
            
        # If we hit a picture, check if we are in a relevant zone
        elif isinstance(item, PictureItem):
            if current_section in relevant_sections:
                try:
                    # Render the image from the document
                    image_obj = item.get_image(doc)
                    buffered = BytesIO()
                    image_obj.save(buffered, format="PNG")
                    
                    # Create typed candidate
                    candidate = ImageCandidate(
                        id=f"img_{len(candidates)}",
                        image=buffered.getvalue(),
                        section_title=current_section,
                        caption=None # Docling might support captions in future or via 'self_ref'
                    )
                    candidates.append(candidate)
                    logger.info(f"Extracted image from relevant section: {current_section}")
                    
                except Exception as e:
                    logger.warning(f"Failed to process image in section {current_section}: {e}")
            else:
                logger.debug(f"Skipping image in irrelevant section: {current_section}")

    logger.info(f"Total extracted candidates: {len(candidates)}")
    return state.model_copy(update={"raw_images": candidates})

async def classify_node(state: WorkflowState) -> WorkflowState:
    logger.info("Classifying images...")
    confirmed_schematics = await llm_svc.identify_schematics(state.raw_images)
    return state.model_copy(update={"filtered_images": confirmed_schematics})

async def save_node(state: WorkflowState) -> WorkflowState:
    logger.info("Saving images and extracted circuit data...")
    
    image_count = await storage_svc.save_filtered_images(
        job_id=state.job_id,
        images=[{"id": img.id, "image": img.image, "section_title": img.section_title, "caption": img.caption} for img in state.filtered_images]
    )
    
    json_count = 0
    if state.extracted_circuits:
        json_count = await storage_svc.save_extracted_circuits(
            job_id=state.job_id,
            extracted_circuits=state.extracted_circuits
        )
    
    logger.info(f"Saved {image_count} images and {json_count} circuit extractions")
    return state.model_copy(update={"saved_count": image_count})


async def extract_schematic_components_node(state: WorkflowState) -> WorkflowState:
    logger.info("Extracting topology from schematic images...")
    
    extracted_results = []
    
    for item in state.filtered_images:
        try:
            image_bytes = item.image
            result = extraction_svc.process_schematic(image_bytes)
            
            circuit_dict: ExtractedCircuitDict = {
                **result,
                "source_image_id": item.id,
                "section_title": item.section_title,
                "caption": item.caption
            }
            extracted_results.append(circuit_dict)
            
            logger.info(f"Extracted {len(result['components'])} components and {len(result['netlist'])} nets from {item.id}")
            
        except Exception as e:
            logger.error(f"Extraction failed for image {item.id}: {e}")
            continue

    return state.model_copy(update={"extracted_circuits": extracted_results})