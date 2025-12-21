from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.constructs import ConstructClasses6
from kicad_modification.parsers.altium.enums import ALTIUM_CLASS_KIND


@dataclass
class Classes6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructClasses6

    """NOT NEEDED YET - LEGACY SETTINGS"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        for altium_class in self.data.classes:
            if altium_class.kind == ALTIUM_CLASS_KIND.NET_CLASS:
                pass

        return kicad_pcb

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass
