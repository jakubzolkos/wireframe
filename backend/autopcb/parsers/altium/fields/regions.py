import sys
from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.items import FilledPolygon
from kicad_modification.parsers.altium.constructs import ConstructRegions6
from kicad_modification.parsers.altium.enums import KICAD_LAYER
from kicad_modification.parsers.altium.utills import get_closed_altium_vertex_chain, get_kicad_layer

ALTIUM_POLYGON_NONE = sys.maxsize & 0xFFFF


@dataclass
class Regions6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructRegions6(extendedvert=False)
    _kicad: CustomAutoPCBBoard | None = field(default=None)

    """DONE"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        self._kicad = kicad_pcb
        for altium_region in self.data.regions:
            if altium_region.polygon != ALTIUM_POLYGON_NONE:
                try:
                    zone = kicad_pcb.zones[altium_region.polygon]
                except IndexError:
                    raise IndexError("Zone with selected Altium polygon index doesn't exist.")

                layer = get_kicad_layer(altium_region.layer)

                if layer == KICAD_LAYER.Undefined_Layer:
                    continue

                outline = get_closed_altium_vertex_chain([vertex.position for vertex in altium_region.outline])
                # holes = [get_closed_altium_vertex_chain(hole.vertices) for hole in altium_region.holes]

                filled_polygon = FilledPolygon(coordinates=outline, layer=layer.name)
                # for hole in holes:
                #     filled_polygon.add_hole(hole)

                # zone.add_filled_polygon(filled_polygon)

                zone.filledPolygons.append(filled_polygon)
                zone.fillSettings.yes = True
                zone.fillSettings.mode = None

                kicad_pcb.zones[altium_region.polygon] = zone

        return self._kicad

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass
