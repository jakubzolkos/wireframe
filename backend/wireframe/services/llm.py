import json
import logging
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types

from wireframe.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.
        Ensure GEMINI_API_KEY is set in your environment variables.
        """
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-3-flash-preview"


    async def identify_schematics(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Iterates through candidates and checks if they are schematics.
        """        
        confirmed = []
        print(f"LLM classifying {len(candidates)} images...")

        for item in candidates:
            is_schematic = await self._classify_single(item["image"], item.get("context", {}))
            
            if is_schematic:
                print(f"Image {item.get('id')} CONFIRMED as reference design.")
                confirmed.append(item)
            else:
                print(f"Image {item.get('id')} rejected.")
                
        return confirmed

    async def _classify_single(self, image: bytes, context: dict) -> bool:
        """
        Sends the image and context to Gemini to determine if it's a schematic.
        """
        try:
            caption = context.get("caption", "No context provided.")

            # 1. Define the Prompt
            prompt_text = f"""
            You are an expert electronics engineer.
            Context for this image: "{caption}"

            Analyze the image provided. Determine if this image represents an 
            "Electronic Circuit Schematic" or a "Reference Design Wiring Diagram".

            Criteria for YES:
            - Contains standard electronic symbols (resistors, capacitors, ICs).
            - Shows connections/wires between components.
            - Represents a functional circuit.

            Criteria for NO:
            - It is a block diagram (boxes with arrows, no component symbols).
            - It is a PCB layout footprint or package dimension drawing.
            - It is a timing diagram or graph.
            - It is a company logo or decorative icon.

            Answer with a JSON object: {{"is_reference_design": boolean, "reasoning": "string"}}
            """

            # 2. Call Gemini
            # Note: The SDK supports passing PIL Images directly
            image = types.Part.from_bytes(
                data=image, mime_type="image/png"
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    prompt_text,
                    image
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0  # Deterministic output
                )
            )

            # 3. Parse Response
            if not response.text:
                print("Empty response from Gemini.")
                return False

            result = json.loads(response.text)
            return result.get("is_reference_design", False)

        except Exception as e:
            print(f"LLM Classification failed: {e}")
            # Fail safe: if LLM crashes, assume False to avoid garbage data
            return False