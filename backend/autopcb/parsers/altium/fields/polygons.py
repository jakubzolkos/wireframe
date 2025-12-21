from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.items import Zone, ZonePolygon
from kicad_modification.parsers.altium.constructs import ConstructPolygons6
from kicad_modification.parsers.altium.enums import ALTIUM_POLYGON_HATCHSTYLE
from kicad_modification.parsers.altium.utills import (
    get_kicad_layers_to_iterate,
    get_shape_line_chain_from_altium_vertices,
    is_internal_altium_plane,
)
from kiutils.items.zones import FillSettings


@dataclass
class Polygons6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructPolygons6

    """DONE - EXCEPT FRACTURING AND OVERLAP PREVENTION"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        for polygon in self.data.polygons:
            outline = get_shape_line_chain_from_altium_vertices(polygon.vertices)

            if polygon.hatchstyle == ALTIUM_POLYGON_HATCHSTYLE.SOLID:
                """TO DO: FOR NON SOLID HATCHSTYLES INFLATE THE OUTLINE: KICAD altium_pcb.cpp line 2096"""
                pass

            zone = Zone()
            zone.net = kicad_pcb.nets[polygon.net].number
            zone.netName = kicad_pcb.nets[polygon.net].name
            zone.locked = polygon.locked
            zone.priority = polygon.pourindex if polygon.pourindex > 0 else 0
            zone.layers = [layer.name for layer in get_kicad_layers_to_iterate(polygon.layer)]
            zone.polygons = [ZonePolygon(outline)]

            if is_internal_altium_plane(polygon.layer):
                zone.priority = 1
                # KiCad computes zone bounding box here

            if polygon.hatchstyle not in (
                ALTIUM_POLYGON_HATCHSTYLE.SOLID.value,
                ALTIUM_POLYGON_HATCHSTYLE.UNKNOWN.value,
            ):
                zone.fillSettings = FillSettings(
                    thermalGap=0.5, thermalBridgeWidth=0.1, mode="hatched", hatchThickness=polygon.trackwidth
                )
                if polygon.hatchstyle == ALTIUM_POLYGON_HATCHSTYLE.DEGREE_45:
                    zone.fillSettings.hatchOrientation = 45
                elif polygon.hatchstyle != ALTIUM_POLYGON_HATCHSTYLE.NONE:
                    zone.fillSettings.hatchGap = polygon.gridsize - polygon.trackwidth
                else:
                    # For hatchstyle -> None, bounding box is computed
                    pass

            """TO DO: SET DISPLAY STYLE: KICAD altium_pcb.cpp line 2225"""

            kicad_pcb.zones.append(zone)

        return kicad_pcb

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass
