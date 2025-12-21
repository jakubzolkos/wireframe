from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.constructs import ConstructRules6
from kicad_modification.parsers.altium.enums import ALTIUM_RULE_KIND


@dataclass
class Rules6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructRules6

    """DONE - EXCEPT LEGACY SETTINGS"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        for rule in self.data.rules:
            match rule.kind:
                case ALTIUM_RULE_KIND.SOLDER_MASK_EXPANSION:
                    kicad_pcb.setup.packToMaskClearance = rule.params.soldermask_expansion
                case ALTIUM_RULE_KIND.PASTE_MASK_EXPANSION:
                    kicad_pcb.setup.padToPasteClearance = rule.params.pastemask_expansion

            return kicad_pcb

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass
