import logging
from typing import List
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from wireframe.config import settings
from wireframe.agents.state import ImageCandidate

logger = logging.getLogger(__name__)

# --- Pydantic Schemas for LLM Responses ---

class SectionRelevance(BaseModel):
    relevant_section_headers: List[str] = Field(
        description="List of exact headers from the provided list that are likely to contain schematic diagrams or reference designs."
    )

class SchematicClassification(BaseModel):
    is_reference_design: bool = Field(
        description="True if the image is an electronic schematic or reference design wiring diagram."
    )
    reasoning: str = Field(description="Short explanation of the classification.")

# ------------------------------------------

class LLMService:
    def __init__(self):
        self.client = genai.Client(api_key='AIzaSyCz4IF-CYow-qkfLwoehCcb2GeoSUL5LMQ')
        self.model_name = "gemini-2.0-flash" # Updated to latest efficient model

    async def identify_relevant_sections(self, headers: List[str]) -> SectionRelevance:
        """
        Analyzes a list of section headers to find those relevant for schematics.
        """
        if not headers:
            logger.warning("No headers provided for analysis.")
            return SectionRelevance(relevant_section_headers=[])

        prompt_text = f"""
        You are an expert electronics engineer analyzing a datasheet structure.
        
        Here is a list of section headers from a chip datasheet:
        {headers}
        
        Identify which of these sections are most likely to contain "Reference Designs", 
        "Typical Applications", "Schematics", or "Application Circuits".
        
        Return ONLY the list of exact header strings that are relevant.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SectionRelevance,
                    temperature=0.0
                )
            )
            
            if response.parsed:
                return response.parsed
            return SectionRelevance(relevant_section_headers=[])
            
        except Exception as e:
            logger.error(f"Failed to identify sections: {e}")
            return SectionRelevance(relevant_section_headers=[])

    async def identify_schematics(self, candidates: List[ImageCandidate]) -> List[ImageCandidate]:
        """
        Classifies images using structured Pydantic outputs.
        """
        confirmed = []
        logger.info(f"LLM classifying {len(candidates)} images...")

        for item in candidates:
            classification = await self._classify_single(item)
            
            if classification.is_reference_design:
                logger.info(f"Image {item.id} CONFIRMED: {classification.reasoning}")
                confirmed.append(item)
            else:
                logger.debug(f"Image {item.id} rejected: {classification.reasoning}")
                
        return confirmed

    async def _classify_single(self, item: ImageCandidate) -> SchematicClassification:
        try:
            prompt_text = f"""
            Context: This image was found in the section "{item.section_title}".
            Caption: "{item.caption or ''}"

            Analyze this image. Is it an "Electronic Circuit Schematic" or "Reference Design"?
            
            Criteria for YES:
            - Standard electronic symbols (resistors, ICs, GND).
            - Wires connecting components.
            
            Criteria for NO:
            - Block diagrams (boxes only).
            - PCB Footprints/Package dimensions.
            - Tables or Graphs.
            """

            image_part = types.Part.from_bytes(
                data=item.image, mime_type="image/png"
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt_text, image_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SchematicClassification,
                    temperature=0.0
                )
            )

            if response.parsed:
                return response.parsed
            
            return SchematicClassification(is_reference_design=False, reasoning="Model returned no parsed response.")

        except Exception as e:
            logger.error(f"Classification failed for {item.id}: {e}")
            return SchematicClassification(is_reference_design=False, reasoning="Error during classification.")
