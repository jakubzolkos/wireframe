from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.constructs import ConstructTexts6


@dataclass
class Texts6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructTexts6

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        return kicad_pcb

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass

    def to_kicad_board_item(self):
        pass

    def to_kicad_footprint_item(self):
        pass

    def to_kicad_board_item_on_layer(self):
        pass

    def to_kicad_footprint_item_on_layer(self):
        pass

    def to_eda_text_settings(self):
        pass
