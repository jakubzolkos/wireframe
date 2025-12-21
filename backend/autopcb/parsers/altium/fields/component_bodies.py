from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.constructs import ConstructComponentBodies6


@dataclass
class ComponentBodies6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructComponentBodies6

    """NOT NEEDED YET - EMBEDDED 3D MODELS"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        return kicad_pcb

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass

    def to_kicad_footprint_item(self, altium_component_body: Container):
        if altium_component_body.model_is_embedded:
            return None
