from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.constructs import ConstructDimensions6
from kicad_modification.parsers.altium.enums import ALTIUM_DIMENSION_KIND


@dataclass
class Dimensions6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructDimensions6

    """NOT NEEDED YET - List[Dimension] in CustomAutoPCBBoard"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        for altium_dimension in self.data.dimensions:
            match altium_dimension.kind:
                case ALTIUM_DIMENSION_KIND.LINEAR:
                    break
                case ALTIUM_DIMENSION_KIND.RADIAL:
                    break
                case ALTIUM_DIMENSION_KIND.LEADER:
                    break
                case ALTIUM_DIMENSION_KIND.CENTER:
                    break
                case _:
                    print("Not yet supported")

        return kicad_pcb

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass
