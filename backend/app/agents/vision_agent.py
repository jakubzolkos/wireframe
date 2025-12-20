from typing import Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from app.core.graph_state import GraphState, Component
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

if settings.openai_api_key:
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.openai_api_key)
else:
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0, api_key=settings.anthropic_api_key)


async def vision_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    await logger.ainfo("vision_agent_start")
    
    graph_state = GraphState(**state)
    
    if not graph_state.schematic_image_path:
        await logger.awarn("no_schematic_image")
        return {"next_node": None}

    prompt = """You are a Netlist Extractor. Analyze this schematic image and extract:
1. Every component with its reference designator (e.g., R1, C1, U1)
2. The value or part number for each component
3. Which pins/nets connect to each component

Return a structured JSON with this format:
{
  "components": [
    {
      "ref_des": "R1",
      "value": "10k",
      "pins": {"1": "VOUT", "2": "GND"},
      "footprint": null
    }
  ],
  "nets": {
    "VOUT": ["R1.1", "C1.1"],
    "GND": ["R1.2", "C1.2"]
  }
}

Be precise and list every component you can identify."""

    try:
        import base64
        from app.services.storage import storage_service
        image_data = await storage_service.download_file(graph_state.schematic_image_path)
        image_b64 = base64.b64encode(image_data).decode()

        from langchain_core.messages import HumanMessage
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ]
        )
        response = await llm.ainvoke([message])

        import json
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        components = [Component(**comp) for comp in result.get("components", [])]
        nets = result.get("nets", {})

        netlist_topology = {}
        for net_name, connections in nets.items():
            netlist_topology[net_name] = connections

        await logger.ainfo("vision_agent_complete", components_count=len(components))

        return {
            "abstract_netlist": [comp.model_dump() for comp in components],
            "netlist_topology": netlist_topology,
            "next_node": "constants_miner",
        }
    except Exception as e:
        await logger.aerror("vision_agent_error", error=str(e))
        return {"error_log": [f"Vision agent error: {str(e)}"], "next_node": "constants_miner"}
