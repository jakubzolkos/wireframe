from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.datatypes import Position
from kicad_modification.parsers.altium.constructs import ConstructBoard6
from kicad_modification.parsers.altium.enums import ALTIUM_LAYER
from kicad_modification.parsers.altium.utills import get_board_outline, get_kicad_layer
from kiutils.items.brditems import LayerToken, StackupLayer


@dataclass
class Board6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructBoard6

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        board = self.data
        kicad_pcb.setup.auxAxisOrigin = Position(board.sheetpos[0], board.sheetpos[1])
        kicad_pcb.setup.gridOrigin = Position(board.sheetpos[0], board.sheetpos[1])

        layercount = 0
        layerid = ALTIUM_LAYER.TOP_LAYER.value
        while layerid < len(board.stackup) and layerid != 0:
            layerid = board.stackup[layerid - 1].next_id
            layercount += 1

        kicad_layer_count = layercount if layercount % 2 == 0 else layercount + 1

        altium_layer_id = ALTIUM_LAYER.TOP_LAYER.value
        while altium_layer_id < len(board.stackup) and altium_layer_id != 0:
            # Retrieve first Altium layer
            layer = board.stackup[altium_layer_id - 1]

            # Add layer token to board layer type list
            kicad_layer = get_kicad_layer(altium_layer_id).name
            layer_name = board.stackup[altium_layer_id - 1].name

            layer_type = "signal"
            if layer.copperthick == 0:
                layer_type = "jumper"
            elif ALTIUM_LAYER.INTERNAL_PLANE_1.value <= altium_layer_id <= ALTIUM_LAYER.INTERNAL_PLANE_16.value:
                layer_type = "power"

            kicad_pcb.layers.append(
                LayerToken(ordinal=altium_layer_id - 1, name=kicad_layer, type=layer_type, userName=layer.name)
            )

            # Add layer to stackup
            kicad_layer = StackupLayer()
            kicad_layer.thickness = layer.copperthick
            kicad_layer.material = layer.dielectricmaterial
            kicad_layer.epsilonR = layer.dielectricconst

            # kicad_pcb.setup.stackup.layers.append(kicad_layer)

            # Move to next stackup layer
            altium_layer_id = board.stackup[altium_layer_id - 1].next_id

            # Encountered layer is unused, appened a stackup layer with zero thickness
            # In case of odd layer count
            if altium_layer_id == 0:
                # Set the layer as unused with zero thickness
                copper_layer = StackupLayer()
                copper_layer.name = "[unused]"
                copper_layer.thickness = 0
                dielectric_layer = StackupLayer()
                dielectric_layer.thickness = 0
                altium_layer_id = board.stackup[altium_layer_id - 1].next_id

        # # Non-copper layers
        for altium_layer_id in range(ALTIUM_LAYER.TOP_OVERLAY.value, ALTIUM_LAYER.BOTTOM_SOLDER.value + 1):
            kicad_layer = get_kicad_layer(altium_layer_id).name
            layer_name = board.stackup[altium_layer_id - 1].name
            kicad_pcb.layers.append(
                LayerToken(ordinal=altium_layer_id - 1, type="signal", name=kicad_layer, userName=layer_name)
            )

        # Mechanical layers
        for altium_layer_id in range(ALTIUM_LAYER.MECHANICAL_1.value, ALTIUM_LAYER.MECHANICAL_16.value + 1):
            kicad_layer = get_kicad_layer(altium_layer_id).name
            layer_name = board.stackup[altium_layer_id - 1].name
            kicad_pcb.layers.append(
                LayerToken(ordinal=altium_layer_id - 1, type="signal", name=kicad_layer, userName=layer_name)
            )

        # Create board outline
        board_outline = get_board_outline(board.vertices)
        for elem in board_outline:
            kicad_pcb.add_gr_item(elem)

        if "Edge.Cuts" not in [layer.name for layer in kicad_pcb.layers]:
            kicad_pcb.layers.append(LayerToken(name="Edge.Cuts", type="user"))

        return kicad_pcb
