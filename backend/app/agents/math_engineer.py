from typing import Any
import json
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from app.core.graph_state import GraphState, ExtractedEquation
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0) if settings.openai_api_key else ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)

STANDARD_VALUES = {
    "R": [100, 120, 150, 180, 220, 270, 330, 390, 470, 560, 680, 820, 1000, 1200, 1500, 1800, 2200, 2700, 3300, 3900, 4700, 5600, 6800, 8200, 10000],
    "C": [0.1e-6, 0.22e-6, 0.47e-6, 1e-6, 2.2e-6, 4.7e-6, 10e-6, 22e-6, 47e-6, 100e-6],
    "L": [1e-6, 2.2e-6, 4.7e-6, 10e-6, 22e-6, 47e-6, 100e-6, 220e-6, 470e-6, 1000e-6],
}


async def math_engineer_node(state: dict[str, Any]) -> dict[str, Any]:
    await logger.ainfo("math_engineer_start")
    
    graph_state = GraphState(**state)
    
    if not graph_state.design_equations:
        await logger.awarn("no_equations")
        return {"next_node": "end"}

    all_variables = {}
    all_variables.update({k: v.value for k, v in graph_state.extracted_constants.items()})
    all_variables.update(graph_state.user_inputs)

    missing_vars: list[str] = []
    equations_to_solve: list[ExtractedEquation] = []

    for eq in graph_state.design_equations:
        missing = [dep for dep in eq.dependencies if dep not in all_variables]
        if missing:
            missing_vars.extend(missing)
        else:
            equations_to_solve.append(eq)

    if missing_vars:
        unique_missing = list(set(missing_vars))
        await logger.ainfo("missing_variables_detected", missing=unique_missing)
        return {
            "missing_variables": unique_missing,
            "next_node": "hitl",
        }

    prompt = f"""Generate a complete, self-contained Python script to solve these design equations.

Available constants and inputs:
{json.dumps(all_variables, indent=2)}

Equations to solve:
{chr(10).join([f"{eq.target_variable}: {eq.python_code}" for eq in equations_to_solve])}

Requirements:
1. Import only standard library (json, math)
2. Solve all equations in dependency order
3. For free variables (not specified), select from standard E24/E96 values:
   - Resistors: {STANDARD_VALUES['R'][:10]}
   - Capacitors: {STANDARD_VALUES['C'][:5]}
   - Inductors: {STANDARD_VALUES['L'][:5]}
4. Output final results as JSON to stdout: {{"R1": 10000, "R2": 32400, ...}}
5. Handle unit conversions (ensure all values in base SI units)

Generate the complete script:"""

    try:
        response = await llm.ainvoke(prompt)
        script = response.content.strip()
        
        if "```python" in script:
            script = script.split("```python")[1].split("```")[0]
        elif "```" in script:
            script = script.split("```")[1].split("```")[0]

        await logger.ainfo("math_engineer_script_generated", script_length=len(script))

        return {
            "calculated_bom": {},
            "next_node": "executor",
            "messages": [{"role": "math_engineer", "content": f"Generated script: {script[:200]}..."}],
        }
    except Exception as e:
        await logger.aerror("math_engineer_error", error=str(e))
        return {"error_log": [f"Math engineer error: {str(e)}"], "next_node": "end"}
