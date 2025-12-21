from enum import Enum
from typing import Dict

from construct import Enum as CEnum


class ConstructEnumBase(Enum):
    @classmethod
    def as_construct(cls, construct_type):
        """
        Converts standard Python enum into a Construct enum.

        Args:
            construct_type: The underlying Construct integer type (e.g., Int8ul, Int8sl).

        Returns:
            A Construct enum object.
        """
        return CEnum(construct_type, **{member.name: member.value for member in cls})


class ALTIUM_UNIT(ConstructEnumBase):
    UNKNOWN = 0
    INCHES = 1
    MILS = 2
    MILLIMETERS = 3
    CENTIMETER = 4


class ALTIUM_CLASS_KIND(ConstructEnumBase):
    UNKNOWN = -1
    NET_CLASS = 0
    SOURCE_SCHEMATIC_CLASS = 1
    FROM_TO = 2
    PAD_CLASS = 3
    LAYER_CLASS = 4
    UNKNOWN_CLASS = 5
    DIFF_PAIR_CLASS = 6
    POLYGON_CLASS = 7


class ALTIUM_DIMENSION_KIND(ConstructEnumBase):
    UNKNOWN = 0
    LINEAR = 1
    ANGULAR = 2
    RADIAL = 3
    LEADER = 4
    DATUM = 5
    BASELINE = 6
    CENTER = 7
    UNKNOWN_2 = 8
    LINEAR_DIAMETER = 9
    RADIAL_DIAMETER = 10


class ALTIUM_REGION_KIND(ConstructEnumBase):
    UNKNOWN = -1
    COPPER = 0
    POLYGON_CUTOUT = 1
    DASHED_OUTLINE = 2
    UNKNOWN_3 = 3
    CAVITY_DEFINITION = 4
    BOARD_CUTOUT = 5


class ALTIUM_RULE_KIND(ConstructEnumBase):
    UNKNOWN = 0
    CLEARANCE = 1
    DIFF_PAIR_ROUTINGS = 2
    HEIGHT = 3
    HOLE_SIZE = 4
    HOLE_TO_HOLE_CLEARANCE = 5
    WIDTH = 6
    PASTE_MASK_EXPANSION = 7
    SOLDER_MASK_EXPANSION = 8
    PLANE_CLEARANCE = 9
    POLYGON_CONNECT = 10
    ROUTING_VIAS = 11

    _string_map: Dict[str, 'ALTIUM_RULE_KIND'] | None = None

    @classmethod
    def from_name(cls, altium_name: str) -> 'ALTIUM_RULE_KIND':
        # Use a method-level cache to store the mapping if it hasn't been created yet
        string_map = {''.join([part.capitalize() for part in kind.name.split('_')]): kind for kind in cls}
        return string_map.get(altium_name, cls.UNKNOWN)


class ALTIUM_CONNECT_STYLE(ConstructEnumBase):
    UNKNOWN = 0
    DIRECT = 1
    RELIEF = 2
    NONE = 3

    @classmethod
    def from_name(cls, altium_name: str) -> 'ALTIUM_CONNECT_STYLE':
        normalized_name = altium_name.strip().upper()
        for kind in cls:
            if kind.name == normalized_name:
                return kind
        return cls.UNKNOWN


class ALTIUM_RECORD(ConstructEnumBase):
    UNKNOWN = -1
    ARC = 1
    PAD = 2
    VIA = 3
    TRACK = 4
    TEXT = 5
    FILL = 6
    REGION = 11
    MODEL = 12


class ALTIUM_PAD_SHAPE(ConstructEnumBase):
    UNKNOWN = 0
    CIRCLE = 1
    RECT = 2
    OCTAGONAL = 3


class ALTIUM_PAD_SHAPE_ALT(ConstructEnumBase):
    UNKNOWN = 0
    CIRCLE = 1
    RECT = 2
    OCTAGONAL = 3
    ROUNDRECT = 9


class ALTIUM_PAD_HOLE_SHAPE(ConstructEnumBase):
    UNKNOWN = -1
    ROUND = 0
    SQUARE = 1
    SLOT = 2


class ALTIUM_PAD_MODE(ConstructEnumBase):
    SIMPLE = 0
    TOP_MIDDLE_BOTTOM = 1
    FULL_STACK = 2


class ALTIUM_MODE(ConstructEnumBase):
    UNKNOWN = -1
    NONE = 0
    RULE = 1
    MANUAL = 2


class ALTIUM_POLYGON_HATCHSTYLE(ConstructEnumBase):
    UNKNOWN = 0
    SOLID = 1
    DEGREE_45 = 2
    DEGREE_90 = 3
    HORIZONTAL = 4
    VERTICAL = 5
    NONE = 6

    @classmethod
    def from_name(cls, altium_name: str) -> 'ALTIUM_POLYGON_HATCHSTYLE':
        match altium_name:
            case "Solid":
                return cls.SOLID
            case "45Degree":
                return cls.DEGREE_45
            case "90Degree":
                return cls.DEGREE_90
            case "Horizontal":
                return cls.HORIZONTAL
            case "Vertical":
                return cls.VERTICAL
            case _:
                return cls.NONE


class ALTIUM_TEXT_POSITION(ConstructEnumBase):
    MANUAL = 0
    LEFT_TOP = 1
    LEFT_CENTER = 2
    LEFT_BOTTOM = 3
    CENTER_TOP = 4
    CENTER_CENTER = 5
    CENTER_BOTTOM = 6
    RIGHT_TOP = 7
    RIGHT_CENTER = 8
    RIGHT_BOTTOM = 9


class ALTIUM_TEXT_TYPE(ConstructEnumBase):
    UNKNOWN = -1
    STROKE = 0
    TRUETYPE = 1
    BARCODE = 2


class AEXTENDED_PRIMITIVE_INFORMATION_TYPE(ConstructEnumBase):
    UNKNOWN = -1
    MASK = 1


class STROKE_FONT_TYPE(ConstructEnumBase):
    DEFAULT = 1
    SANSSERIF = 2
    SERIF = 3


class ALTIUM_ZONE_FILL_MODE(ConstructEnumBase):
    POLYGONS = 0
    HATCH_PATTERN = 1


class ALTIUM_LAYER(ConstructEnumBase):
    UNKNOWN = 0
    TOP_LAYER = 1
    MID_LAYER_1 = 2
    MID_LAYER_2 = 3
    MID_LAYER_3 = 4
    MID_LAYER_4 = 5
    MID_LAYER_5 = 6
    MID_LAYER_6 = 7
    MID_LAYER_7 = 8
    MID_LAYER_8 = 9
    MID_LAYER_9 = 10
    MID_LAYER_10 = 11
    MID_LAYER_11 = 12
    MID_LAYER_12 = 13
    MID_LAYER_13 = 14
    MID_LAYER_14 = 15
    MID_LAYER_15 = 16
    MID_LAYER_16 = 17
    MID_LAYER_17 = 18
    MID_LAYER_18 = 19
    MID_LAYER_19 = 20
    MID_LAYER_20 = 21
    MID_LAYER_21 = 22
    MID_LAYER_22 = 23
    MID_LAYER_23 = 24
    MID_LAYER_24 = 25
    MID_LAYER_25 = 26
    MID_LAYER_26 = 27
    MID_LAYER_27 = 28
    MID_LAYER_28 = 29
    MID_LAYER_29 = 30
    MID_LAYER_30 = 31
    BOTTOM_LAYER = 32
    TOP_OVERLAY = 33
    BOTTOM_OVERLAY = 34
    TOP_PASTE = 35
    BOTTOM_PASTE = 36
    TOP_SOLDER = 37
    BOTTOM_SOLDER = 38
    INTERNAL_PLANE_1 = 39
    INTERNAL_PLANE_2 = 40
    INTERNAL_PLANE_3 = 41
    INTERNAL_PLANE_4 = 42
    INTERNAL_PLANE_5 = 43
    INTERNAL_PLANE_6 = 44
    INTERNAL_PLANE_7 = 45
    INTERNAL_PLANE_8 = 46
    INTERNAL_PLANE_9 = 47
    INTERNAL_PLANE_10 = 48
    INTERNAL_PLANE_11 = 49
    INTERNAL_PLANE_12 = 50
    INTERNAL_PLANE_13 = 51
    INTERNAL_PLANE_14 = 52
    INTERNAL_PLANE_15 = 53
    INTERNAL_PLANE_16 = 54
    DRILL_GUIDE = 55
    KEEP_OUT_LAYER = 56
    MECHANICAL_1 = 57
    MECHANICAL_2 = 58
    MECHANICAL_3 = 59
    MECHANICAL_4 = 60
    MECHANICAL_5 = 61
    MECHANICAL_6 = 62
    MECHANICAL_7 = 63
    MECHANICAL_8 = 64
    MECHANICAL_9 = 65
    MECHANICAL_10 = 66
    MECHANICAL_11 = 67
    MECHANICAL_12 = 68
    MECHANICAL_13 = 69
    MECHANICAL_14 = 70
    MECHANICAL_15 = 71
    MECHANICAL_16 = 72
    DRILL_DRAWING = 73
    MULTI_LAYER = 74
    CONNECTIONS = 75
    BACKGROUND = 76
    DRC_ERROR_MARKERS = 77
    SELECTIONS = 78
    VISIBLE_GRID_1 = 79
    VISIBLE_GRID_2 = 80
    PAD_HOLES = 81
    VIA_HOLES = 82

    @property
    def as_kicad(self):
        return self.value

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return self.value == other.value


class KICAD_LAYER(ConstructEnumBase):
    Undefined_Layer = -1
    Unselected_Layer = -2

    F_Cu = 0
    B_Cu = 2
    In1_Cu = 4
    In2_Cu = 6
    In3_Cu = 8
    In4_Cu = 10
    In5_Cu = 12
    In6_Cu = 14
    In7_Cu = 16
    In8_Cu = 18
    In9_Cu = 20
    In10_Cu = 22
    In11_Cu = 24
    In12_Cu = 26
    In13_Cu = 28
    In14_Cu = 30
    In15_Cu = 32
    In16_Cu = 34
    In17_Cu = 36
    In18_Cu = 38
    In19_Cu = 40
    In20_Cu = 42
    In21_Cu = 44
    In22_Cu = 46
    In23_Cu = 48
    In24_Cu = 50
    In25_Cu = 52
    In26_Cu = 54
    In27_Cu = 56
    In28_Cu = 58
    In29_Cu = 60
    In30_Cu = 62

    F_Mask = 1
    B_Mask = 3

    F_Silks = 5
    B_Silks = 7
    F_Adhes = 9
    B_Adhes = 11
    F_Paste = 13
    B_Paste = 15

    Dwgs_User = 17
    Cmts_User = 19
    Eco1_User = 21
    Eco2_User = 23

    Edge_Cuts = 25
    Margin = 27

    B_CrtYd = 29
    F_CrtYd = 31

    B_Fab = 33
    F_Fab = 35

    Rescue = 37

    User_1 = 39
    User_2 = 41
    User_3 = 43
    User_4 = 45
    User_5 = 47
    User_6 = 49
    User_7 = 51
    User_8 = 53
    User_9 = 55

    KICAD_LAYER_COUNT = 64

    @staticmethod
    def is_copper_layer(value):
        try:
            return KICAD_LAYER(value).name.endswith("Cu")
        except ValueError:
            return False

    @property
    def name(self):
        """Obtains the name of the enum type in a format expected by KiCad symbolic expression."""
        return super().name.replace("_", ".")
