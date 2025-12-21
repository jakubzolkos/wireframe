from dataclasses import dataclass, field
from typing import Dict, List

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.constructs import ConstructExtendedPrimitiveInformation


@dataclass
class ExtendedPrimitiveInformation:
    data: Container | None = field(default=None)
    struct: Struct = ConstructExtendedPrimitiveInformation
    extended_primitive_information_map: Dict[str, List[Container]] = field(default_factory=dict)

    """DONE"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        if not self.data or not hasattr(self.data, 'extended_pad_primitives'):
            return kicad_pcb

        for primitive_info in self.data.extended_pad_primitives:
            object_id = primitive_info.primitiveObjectId
            index = primitive_info.primitiveIndex

            if object_id not in self.extended_primitive_information_map:
                self.extended_primitive_information_map[object_id] = []

            primitive_list = self.extended_primitive_information_map[object_id]
            if len(primitive_list) <= index:
                primitive_list.extend([None] * (index - len(primitive_list) + 1))

            primitive_list[index] = primitive_info

        return kicad_pcb
