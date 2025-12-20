import uuid
import networkx as nx
from typing import Any
from app.core.graph_state import Component, GraphState
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYMBOL_LIBRARIES = {
    "R": "Device:R",
    "C": "Device:C",
    "L": "Device:L",
    "D": "Device:D",
    "Q": "Device:Q_NPN_GND",
    "U": "Device:IC",
}


def generate_kicad_schematic(state: GraphState) -> str:
    components = state.abstract_netlist
    calculated_bom = state.calculated_bom
    netlist_topology = state.netlist_topology

    positions = _calculate_positions(components, netlist_topology)

    schematic_parts: list[str] = []
    schematic_parts.append("(kicad_sch (version 20230121) (generator eda_backend)")

    for comp in components:
        value = calculated_bom.get(comp.ref_des, comp.value)
        x, y = positions.get(comp.ref_des, (0.0, 0.0))
        sexpr = _create_component_sexpr(comp, value, x, y)
        schematic_parts.append(sexpr)

    for net_name, connections in netlist_topology.items():
        net_sexpr = _create_net_sexpr(net_name, connections, positions)
        if net_sexpr:
            schematic_parts.append(net_sexpr)

    schematic_parts.append(")")

    return "\n".join(schematic_parts)


def _create_component_sexpr(comp: Component, value: str, x_pos: float, y_pos: float) -> str:
    comp_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{comp.ref_des}_{value}")
    lib_id = _get_library_id(comp.ref_des)

    at_expr = f"(at {x_pos:.2f} {y_pos:.2f} 0)"
    font_effects = "(effects (font (size 1.27 1.27)) (justify left))"

    pins_sexpr = ""
    for pin_num, pin_name in comp.pins.items():
        pin_uuid = uuid.uuid5(comp_uuid, f"pin{pin_num}")
        pins_sexpr += f'\n      (pin "{pin_num}" (uuid "{pin_uuid}"))'

    sexpr = f"""  (symbol (lib_id "{lib_id}") {at_expr} (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid "{comp_uuid}")
    (property "Reference" "{comp.ref_des}" (at {x_pos:.2f} {y_pos - 2.54:.2f} 0)
      {font_effects}
    )
    (property "Value" "{value}" (at {x_pos:.2f} {y_pos + 2.54:.2f} 0)
      {font_effects}
    )"""
    
    if comp.footprint:
        sexpr += f'''
    (property "Footprint" "{comp.footprint}" (at {x_pos:.2f} {y_pos:.2f} 0)
      (effects (font (size 1.27 1.27)) hide)
    )'''

    sexpr += pins_sexpr
    sexpr += "\n  )"

    return sexpr


def _get_library_id(ref_des: str) -> str:
    prefix = ref_des[0] if ref_des else "R"
    return SYMBOL_LIBRARIES.get(prefix, "Device:R")


def _create_net_sexpr(net_name: str, connections: list[str], positions: dict[str, tuple[float, float]]) -> str:
    if len(connections) < 2:
        return ""

    net_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"net_{net_name}")
    net_parts: list[str] = [f'  (net (code 1) (name "{net_name}")']

    for conn in connections:
        if "." in conn:
            ref_des, pin = conn.split(".", 1)
            if ref_des in positions:
                x, y = positions[ref_des]
                net_parts.append(f'    (node (ref "{ref_des}") (pin "{pin}"))')

    net_parts.append("  )")
    return "\n".join(net_parts)


def _calculate_positions(components: list[Component], netlist: dict[str, list[str]]) -> dict[str, tuple[float, float]]:
    if not components:
        return {}

    G = nx.Graph()

    for comp in components:
        G.add_node(comp.ref_des)

    for net_name, connections in netlist.items():
        node_list = [conn.split(".")[0] for conn in connections if "." in conn]
        for i in range(len(node_list) - 1):
            G.add_edge(node_list[i], node_list[i + 1])

    try:
        pos = nx.spring_layout(G, k=50, iterations=50)
    except Exception:
        pos = {comp.ref_des: (i * 50.0, 0.0) for i, comp in enumerate(components)}

    scaled_pos = {ref: (x * 25.4, y * 25.4) for ref, (x, y) in pos.items()}
    return scaled_pos
