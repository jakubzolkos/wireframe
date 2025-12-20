from typing import Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from app.core.graph_state import GraphState, ExtractedConstant
from app.config import settings
from app.utils.logging import get_logger
import json
import re

logger = get_logger(__name__)

llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0) if settings.openai_api_key else ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)

STANDARD_VARIABLES = [
    "V_ref", "I_sw_limit", "V_uvlo", "V_ovp", "f_sw", "I_q", "V_in_min", "V_in_max",
    "V_out", "I_out_max", "efficiency", "R_ds_on", "V_f", "I_leakage",
]


async def constants_miner_node(state: dict[str, Any]) -> dict[str, Any]:
    await logger.ainfo("constants_miner_start")
    
    graph_state = GraphState(**state)
    
    table_chunks = [chunk for chunk in graph_state.pdf_chunks if "table" in chunk.chunk_type.lower() or "electrical" in chunk.content.lower()[:200]]
    
    if not table_chunks:
        await logger.awarn("no_table_chunks")
        return {"next_node": "equation_extractor"}

    extracted_constants = dict(graph_state.extracted_constants)

    for chunk in table_chunks:
        prompt = f"""Extract electrical characteristics from this table data. Look for standard variables like:
{', '.join(STANDARD_VARIABLES)}

For each value found:
1. Identify the standard variable name (e.g., "Feedback Voltage" -> V_ref)
2. Extract the "Typical" value
3. Note the unit
4. Provide source context

Return JSON format:
{{
  "constants": [
    {{
      "name": "V_ref",
      "value": 0.8,
      "unit": "V",
      "source_context": "Feedback Voltage (Typical): 0.8V"
    }}
  ]
}}

Table data:
{chunk.content[:2000]}"""

        try:
            response = await llm.ainvoke(prompt)
            content = response.content
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())
            
            for const_data in result.get("constants", []):
                const = ExtractedConstant(**const_data)
                value = _convert_to_si(const.value, const.unit)
                const.value = value
                const.unit = _normalize_unit(const.unit)
                extracted_constants[const.name] = const
                
            await logger.ainfo("constants_extracted", count=len(result.get("constants", [])))
        except Exception as e:
            await logger.awarn("constant_extraction_failed", error=str(e), chunk_page=chunk.page_number)

    await logger.ainfo("constants_miner_complete", total_constants=len(extracted_constants))

    return {
        "extracted_constants": {k: v.model_dump() for k, v in extracted_constants.items()},
        "next_node": "equation_extractor",
    }


def _convert_to_si(value: float, unit: str) -> float:
    unit_lower = unit.lower()
    if unit_lower in ["mv", "millivolt"]:
        return value / 1000.0
    if unit_lower in ["ma", "milliamp"]:
        return value / 1000.0
    if unit_lower in ["ua", "microamp"]:
        return value / 1000000.0
    if unit_lower in ["mhz", "megahertz"]:
        return value * 1000000.0
    if unit_lower in ["khz", "kilohertz"]:
        return value * 1000.0
    return value


def _normalize_unit(unit: str) -> str:
    unit_lower = unit.lower()
    if unit_lower in ["mv", "millivolt"]:
        return "V"
    if unit_lower in ["ma", "milliamp"]:
        return "A"
    if unit_lower in ["ua", "microamp"]:
        return "A"
    if unit_lower in ["mhz", "megahertz"]:
        return "Hz"
    if unit_lower in ["khz", "kilohertz"]:
        return "Hz"
    return unit
