import io
from dataclasses import dataclass, field
from typing import Any, Dict

import compoundfiles
import construct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.fields import *


@dataclass
class AltiumPCB:
    arcs6: Arcs6 | None = field(default=None)
    nets6: Nets6 | None = field(default=None)
    pads6: Pads6 | None = field(default=None)
    texts6: Texts6 | None = field(default=None)
    vias6: Vias6 | None = field(default=None)
    board6: Board6 | None = field(default=None)
    fills6: Fills6 | None = field(default=None)
    classes6: Classes6 | None = field(default=None)
    tracks6: Tracks6 | None = field(default=None)
    regions6: Regions6 | None = field(default=None)
    shapebasedregions6: ShapeBasedRegions6 | None = field(default=None)
    polygons6: Polygons6 | None = field(default=None)
    rules6: Rules6 | None = field(default=None)
    dimensions6: Dimensions6 | None = field(default=None)
    components6: Components6 | None = field(default=None)
    extendedprimitiveinformation: ExtendedPrimitiveInformation | None = field(default=None)
    filepath: str = field(default=None)

    _struct_map: Dict[str, Any] = field(
        default_factory=lambda: {
            "Arcs6": Arcs6,
            "Nets6": Nets6,
            "Pads6": Pads6,
            "Texts6": Texts6,
            "Vias6": Vias6,
            "Board6": Board6,
            "Fills6": Fills6,
            "Classes6": Classes6,
            "Tracks6": Tracks6,
            "Regions6": Regions6,
            "ShapeBasedRegions6": ShapeBasedRegions6,
            "Rules6": Rules6,
            "Polygons6": Polygons6,
            "Dimensions6": Dimensions6,
            "Components6": Components6,
            "ExtendedPrimitiveInformation": ExtendedPrimitiveInformation,
        },
        init=False,
    )

    def _parse_compound_file(self, altium_doc):
        """Common logic for parsing the compound file."""
        print(altium_doc.root)
        for component in altium_doc.root:
            if component.name in self._struct_map:
                try:
                    with altium_doc.open(component['Data']) as component_stream:
                        altium_component = self._struct_map[component.name]()
                        data = altium_component.struct.parse(component_stream.read())

                        altium_component.data = data
                        setattr(self, component.name.lower(), altium_component)
                except construct.core.StreamError as e:
                    print(component.name, e)

        self.compound_file = altium_doc

    @classmethod
    def from_file(cls, filepath: str) -> "AltiumPCB":
        """Imports an Altium binary file and parses it into Python constructs."""
        acceptable_extensions = [".pcbdoc", ".PcbDoc"]
        if not any(filepath.endswith(extension) for extension in acceptable_extensions):
            raise TypeError("Invalid Altium binary file.")

        instance = cls()
        instance.filepath = filepath

        with compoundfiles.CompoundFileReader(filepath) as altium_doc:
            instance._parse_compound_file(altium_doc)

        return instance

    @classmethod
    def from_binary_string(cls, byte_stream: bytes) -> "AltiumPCB":
        """Imports an Altium binary byte stream and parses it into Python constructs."""
        if not isinstance(byte_stream, bytes):
            raise TypeError("Input must be a byte string.")

        instance = cls()

        with io.BytesIO(byte_stream) as stream:
            with compoundfiles.CompoundFileReader(stream) as altium_doc:
                instance._parse_compound_file(altium_doc)

        return instance

    def from_kicad(self, kicad_pcb: CustomAutoPCBBoard):
        """Parses a KiCAD board into an Altium construct"""
        pass

    def to_kicad(self) -> CustomAutoPCBBoard:
        """Iterates through Altium structures and updates the KiCAD board with parsed PCB information"""
        kicad_pcb = CustomAutoPCBBoard()
        kicad_pcb.version = "20240108"
        kicad_pcb.generator = "pcbnew"

        ordered_attrs = [
            "board6",
            "components6",
            "nets6",
            "classes6",
            "rules6",
            "dimensions6",
            "polygons6",
            "arcs6",
            "pads6",
            "vias6",
            "tracks6",
            "texts6",
            "fills6",
            "regions6",
            "shapebasedregions6",
        ]

        for attr_name in ordered_attrs:
            if attr_name in ('compound_file', 'filepath', '_struct_map', 'rules6', 'dimensions6'):
                continue
            attr_value = getattr(self, attr_name)
            kicad_pcb = attr_value.update_kicad_pcb(kicad_pcb)

        # # Fix Zone priorities as Altium stores them in opposite order
        highest_pour_index = max(zone.priority for zone in kicad_pcb.zones if zone.priority is not None)
        for zone in kicad_pcb.zones:
            if zone.priority == 1000:
                if highest_pour_index >= 1000:
                    zone.priority = highest_pour_index + 1
                zone.priority = max(highest_pour_index - zone.priority, 0)

        return kicad_pcb

    def export(self):
        """Builds parsed Altium constructs back into binary file"""
        return self.filepath


if __name__ == '__main__':
    altium_pcb = AltiumPCB.from_file("test/PiMX8MP_r0.2.PcbDoc")
    kicad = altium_pcb.to_kicad()
    print(kicad.arcs)
    with open("test/test.kicad_pcb", 'w', encoding=None) as outfile:
        outfile.write(kicad.to_sexpr())

    # from kiutils.utils import sexpr

    # with open("test/test_ref.kicad_pcb", 'r', encoding=None) as f:
    #     item = CustomAutoPCBBoard.from_sexpr(sexpr.parse_sexp(f.read()))
    #     print(item.arcs)
