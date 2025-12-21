from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.constructs import ConstructNets6
from kiutils.board import Net


@dataclass
class Nets6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructNets6

    """DONE"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        kicad_pcb.nets.append(Net(0, ""))
        for index, altium_net in enumerate(self.data.nets):
            net = Net(number=index + 1, name=altium_net.name)
            kicad_pcb.nets.append(net)

        return kicad_pcb

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass
