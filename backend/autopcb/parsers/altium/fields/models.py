from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.constructs import ConstructModels6


@dataclass
class Models6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructModels6

    """NOT NEEDED YET - EMBEDDED MODELS"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        return kicad_pcb

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass
