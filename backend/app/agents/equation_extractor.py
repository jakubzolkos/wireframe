from typing import Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from app.core.graph_state import GraphState, ExtractedEquation
from app.config import settings
from app.utils.logging import get_logger
import json
import re

logger = get_logger(__name__)

llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0) if settings.openai_api_key else ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)


async def equation_extractor_node(state: dict[str, Any]) -> dict[str, Any]:
    await logger.ainfo("equation_extractor_start")
    
    graph_state = GraphState(**state)
    
    prose_chunks = [chunk for chunk in graph_state.pdf_chunks if "prose" in chunk.chunk_type.lower() or "application" in chunk.content.lower()[:200]]
    
    if not prose_chunks:
        await logger.awarn("no_prose_chunks")
        return {"next_node": "math_engineer"}

    design_equations = list(graph_state.design_equations)

    for chunk in prose_chunks:
        prompt = f"""Extract design equations from this Application Information section. Look for formulas that calculate component values like:
- Feedback resistor values (R1, R2)
- Inductor values (L)
- Capacitor values (C)
- Compensation network values

For each equation found:
1. Extract the LaTeX representation
2. Convert to Python code
3. Identify the target variable (what we're solving for)
4. List all dependencies (variables needed to solve)

Return JSON format:
{{
  "equations": [
    {{
      "target_variable": "R2",
      "latex_raw": "R_2 = R_1 \\times (V_{{out}}/V_{{ref}} - 1)",
      "python_code": "R2 = R1 * (V_out / V_ref - 1)",
      "dependencies": ["R1", "V_out", "V_ref"]
    }}
  ]
}}

Text:
{chunk.content[:3000]}"""

        try:
            response = await llm.ainvoke(prompt)
            content = response.content
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())
            
            for eq_data in result.get("equations", []):
                eq = ExtractedEquation(**eq_data)
                design_equations.append(eq)
                
            await logger.ainfo("equations_extracted", count=len(result.get("equations", [])))
        except Exception as e:
            await logger.awarn("equation_extraction_failed", error=str(e), chunk_page=chunk.page_number)

    await logger.ainfo("equation_extractor_complete", total_equations=len(design_equations))

    return {
        "design_equations": [eq.model_dump() for eq in design_equations],
        "next_node": "math_engineer",
    }
