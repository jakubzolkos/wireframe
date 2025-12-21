from construct import (
    Array,
    Byte,
    Bytes,
    Computed,
    ExprAdapter,
    FixedSized,
    Flag,
    Float64l,
    GreedyBytes,
    If,
    IfThenElse,
    Int8sl,
    Int8ul,
    Int16ul,
    Int32sl,
    Int32ul,
    Padding,
    Pass,
    Prefixed,
    RepeatUntil,
    Struct,
    Switch,
    Tell,
    this,
)
from kicad_modification.parsers.altium.converters import convert_to_kicad_unit, format_internal_units
from kicad_modification.parsers.altium.enums import *
from kicad_modification.parsers.altium.readers import AltiumPropertyReader
from kicad_modification.parsers.altium.utills import get_remaining_bytes

# ----------------- FIELDS -----------------

KICAD_UNIT = lambda size=Int32sl: ExprAdapter(
    size, decoder=lambda obj, ctx: format_internal_units(convert_to_kicad_unit(obj)), encoder=lambda obj, ctx: obj
)

KICAD_UNIT_X = lambda size=Int32sl: ExprAdapter(
    size, decoder=lambda obj, ctx: format_internal_units(convert_to_kicad_unit(obj)), encoder=lambda obj, ctx: obj
)

KICAD_UNIT_Y = lambda size=Int32sl: ExprAdapter(
    size, decoder=lambda obj, ctx: -format_internal_units(convert_to_kicad_unit(obj)), encoder=lambda obj, ctx: obj
)

POSITION = lambda size=Int32sl: Struct("x" / KICAD_UNIT_X(size), "y" / KICAD_UNIT_Y(size))

VECTOR3D = Struct("x" / Float64l, "y" / Float64l, "z" / Float64l)

SIZE = Struct("x" / KICAD_UNIT(), "y" / KICAD_UNIT())

WXSIZE = Struct("width" / Int32ul, "height" / Int32ul)

WXSTRING = Struct(
    "length" / Byte,
    "raw_string" / Bytes(lambda ctx: ctx.length),
    "string" / Computed(lambda ctx: ctx.raw_string.decode('latin1')),
)

VERTEX = Struct(
    "isRound" / Flag,
    "radius" / Int32ul,
    "startangle" / Float64l,
    "endangle" / Float64l,
    "position" / POSITION(),
    "center" / SIZE,
)

PROPERTIES = ExprAdapter(
    Struct(
        "length" / Int32ul,
        "data" / Bytes(lambda ctx: ctx.length & 0x00FFFFFF),
    ),
    decoder=lambda obj, ctx: AltiumPropertyReader(obj['length'], obj['data']),
    encoder=lambda obj, ctx: obj,
)

SKIP = lambda n_bytes: Bytes(n_bytes)


# ------------- ALTIUM BINARIES ------------

ConstructExtendedPrimitiveInformation = Struct(
    "extended_pad_primitives"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "properties" / PROPERTIES,
            "primitiveIndex" / Computed(lambda ctx: ctx.properties.read_int("PRIMITIVEINDEX", -1)),
            "primitiveObjectId" / Computed(lambda ctx: ctx.properties.read_string("PRIMITIVEOBJECTID", "")),
            "type" / Computed(lambda ctx: ctx.properties.read_string("TYPE", "")),
            "pastemaskexpansionmode" / Computed(lambda ctx: ctx.properties.read_string("PASTEMASKEXPANSIONMODE", "")),
            "pastemaskexpansionmanual"
            / Computed(lambda ctx: ctx.properties.read_kicad_unit("PASTEMASKEXPANSION_MANUAL", "0mil")),
            "soldermaskexpansionmode" / Computed(lambda ctx: ctx.properties.read_string("SOLDERMASKEXPANSIONMODE", "")),
            "soldermaskexpansionmanual"
            / Computed(lambda ctx: ctx.properties.read_kicad_unit("SOLDERMASKEXPANSION_MANUAL", "0mil")),
        ),
    )
)

ConstructBoard6 = Struct(
    "properties" / PROPERTIES,
    "sheetpos"
    / Computed(
        lambda ctx: (
            ctx.properties.read_kicad_unit("SHEETX", "0mil"),
            -ctx.properties.read_kicad_unit("SHEETY", "0mil"),
        )
    ),
    "sheetsize"
    / Computed(
        lambda ctx: (
            ctx.properties.read_kicad_unit("SHEETWIDTH", "0mil"),
            ctx.properties.read_kicad_unit("SHEETHEIGHT", "0mil"),
        )
    ),
    "layercount" / Computed(lambda ctx: ctx.properties.read_int("LAYERSETSCOUNT", 1) + 1),
    "stackup" / Computed(lambda ctx: ctx.properties.read_layer_stackup()),
    "vertices" / Computed(lambda ctx: ctx.properties.read_board_polygons()),
)

ConstructComponents6 = Struct(
    "components"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "properties" / PROPERTIES,
            "layer" / Computed(lambda ctx: ctx.properties.read_string("LAYER", "")),
            "position"
            / Struct(
                "x" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("X", "0mil")),
                "y" / Computed(lambda ctx: -ctx._.properties.read_kicad_unit("Y", "0mil")),
            ),
            "rotation" / Computed(lambda ctx: ctx.properties.read_double("ROTATION", 0)),
            "locked" / Computed(lambda ctx: ctx.properties.read_bool("LOCKED", False)),
            "nameon" / Computed(lambda ctx: ctx.properties.read_bool("NAMEON", True)),
            "commenton" / Computed(lambda ctx: ctx.properties.read_bool("COMMENTON", False)),
            "sourcedesignator" / Computed(lambda ctx: ctx.properties.read_string("SOURCEDESIGNATOR", "")),
            "sourcefootprintlibrary"
            / Computed(lambda ctx: ctx.properties.read_unicode_string("SOURCEFOOTPRINTLIB", "")),
            "pattern" / Computed(lambda ctx: ctx.properties.read_unicode_string("PATTERN", "")),
            "sourcecomponentlibrary" / Computed(lambda ctx: ctx.properties.read_string("SOURCECOMPONENTLIBRARY", "")),
            "sourcelibreference" / Computed(lambda ctx: ctx.properties.read_string("SOURCELIBREFERENCE", "")),
            "nameautoposition" / Computed(lambda ctx: ctx.properties.read_int("NAMEAUTOPOSITION", 0)),
            "commentautoposition" / Computed(lambda ctx: ctx.properties.read_int("COMMENTAUTOPOSITION", 0)),
        ),
    )
)

ConstructDimensions6 = Struct(
    "dimensions"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "skip_2" / SKIP(2),
            "properties" / PROPERTIES,
            "layer" / Computed(lambda ctx: ctx.properties.read_string("LAYER", "")),
            "kind" / Computed(lambda ctx: ALTIUM_DIMENSION_KIND(ctx.properties.read_int("DIMENSIONKIND", ""))),
            "textformat" / Computed(lambda ctx: ctx.properties.read_string("TEXTFORMAT", "")),
            "textprefix" / Computed(lambda ctx: ctx.properties.read_string("TEXTPREFIX", "")),
            "textsuffix" / Computed(lambda ctx: ctx.properties.read_string("TEXTSUFFIX", "")),
            "height" / Computed(lambda ctx: ctx.properties.read_kicad_unit("HEIGHT", "0mil")),
            "angle" / Computed(lambda ctx: ctx.properties.read_double("ANGLE", 0.0)),
            "linewidth" / Computed(lambda ctx: ctx.properties.read_kicad_unit("LINEWIDTH", "10mil")),
            "textheight" / Computed(lambda ctx: ctx.properties.read_kicad_unit("LINEHEIGHT", "10mil")),
            "textlinewidth" / Computed(lambda ctx: ctx.properties.read_kicad_unit("TEXTLINEWIDTH", "6mil")),
            "textprecision" / Computed(lambda ctx: ctx.properties.read_int("TEXTPRECISION", 2)),
            "textbold" / Computed(lambda ctx: ctx.properties.read_bool("TEXTLINEWIDTH", False)),
            "textitalic" / Computed(lambda ctx: ctx.properties.read_bool("ITALIC", False)),
            "textgap" / Computed(lambda ctx: ctx.properties.read_bool("TEXTGAP", "10mil")),
            "arrowsize" / Computed(lambda ctx: ctx.properties.read_kicad_unit("ARROWSIZE", "60mil")),
            "text_position_raw" / Computed(lambda ctx: ctx.properties.read_string("TEXTPOSITION", "")),
            "xy1"
            / Struct(
                "x" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("X1", "0mil")),
                "y" / Computed(lambda ctx: -ctx._.properties.read_kicad_unit("Y1", "0mil")),
            ),
            "refcount" / Computed(lambda ctx: ctx.properties.read_int("REFERENCES_COUNT", 0)),
            "reference_points"
            / Array(
                lambda ctx: ctx.refcount,
                Struct(
                    "x"
                    / Computed(lambda ctx: ctx._.properties.read_kicad_unit(f"REFERENCE{ctx._index}POINTX", "0mil")),
                    "y"
                    / Computed(lambda ctx: -ctx._.properties.read_kicad_unit(f"REFERENCE{ctx._index}POINTY", "0mil")),
                ),
            ),
            "text_points" / Computed(lambda ctx: ctx.properties.read_text_points()),
            "dimensionunit" / Computed(lambda ctx: ctx.properties.read_string("TEXTDIMENSIONUNIT", "Millimeters")),
            "textunit"
            / Computed(
                lambda ctx: {
                    "Inches": ALTIUM_UNIT.INCHES,
                    "Mils": ALTIUM_UNIT.MILS,
                    "Millimeters": ALTIUM_UNIT.MILLIMETERS,
                    "Centimeters": ALTIUM_UNIT.CENTIMETER,
                }.get(ctx.dimensionunit, ALTIUM_UNIT.UNKNOWN)
            ),
        ),
    )
)

ConstructModels6 = Struct(
    "properties" / PROPERTIES,
    "name" / Computed(lambda ctx: ctx.properties.read_string("NAME", "")),
    "id" / Computed(lambda ctx: ctx.properties.read_string("ID", "")),
    "is_embedded" / Computed(lambda ctx: ctx.properties.read_bool("EMBED", False)),
    "rotation"
    / Computed(
        lambda ctx: (
            ctx.properties.read_double("ROTX", 0.0),
            ctx.properties.read_double("ROTY", 0.0),
            ctx.properties.read_double("ROTZ", 0.0),
        )
    ),
    "z_offset" / Computed(lambda ctx: ctx.properties.read_double("DZ", 0.0)),
    "checksum" / Computed(lambda ctx: ctx.properties.read_int("CHECKSUM", 0)),
    "remainder" / GreedyBytes,
)

ConstructNets6 = Struct(
    "nets"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "properties" / PROPERTIES,
            "name" / Computed(lambda ctx: ctx.properties.read_string("NAME", "")),
        ),
    )
)

ConstructPolygons6 = Struct(
    "polygons"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "properties" / PROPERTIES,
            "layer" / Computed(lambda ctx: ctx.properties.read_string("LAYER", "")),
            "net" / Computed(lambda ctx: ctx.properties.read_int("NET", (2**16) - 1)),
            "locked" / Computed(lambda ctx: ctx.properties.read_bool("LOCKED", False)),
            "gridsize" / Computed(lambda ctx: ctx.properties.read_kicad_unit("GRIDSIZE", "0mil")),
            "trackwidth" / Computed(lambda ctx: ctx.properties.read_kicad_unit("TRACKWIDTH", "0mil")),
            "minprimlength" / Computed(lambda ctx: ctx.properties.read_kicad_unit("MINPRIMLENGTH", "0mil")),
            "useoctagons" / Computed(lambda ctx: ctx.properties.read_bool("USEOCTAGONS", False)),
            "pourindex" / Computed(lambda ctx: ctx.properties.read_int("POURINDEX", 0)),
            "hatchstyle"
            / Computed(lambda ctx: ALTIUM_POLYGON_HATCHSTYLE.from_name(ctx.properties.read_string("HATCHSTYLE", ""))),
            "vertices" / Computed(lambda ctx: ctx.properties.read_board_polygons()),
        ),
    )
)

ConstructRules6 = Struct(
    "rules"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "skip_2" / SKIP(2),
            "properties" / PROPERTIES,
            "name" / Computed(lambda ctx: ctx.properties.read_string("NAME", "")),
            "priority" / Computed(lambda ctx: ctx.properties.read_int("PRIORITY", 1)),
            "scope1expr" / Computed(lambda ctx: ctx.properties.read_string("SCOPE1EXPRESSION", "")),
            "scope2expr" / Computed(lambda ctx: ctx.properties.read_string("SCOPE2EXPRESSION", "")),
            "rulekind" / Computed(lambda ctx: ctx.properties.read_string("RULEKIND", "")),
            "kind" / Computed(lambda ctx: ALTIUM_RULE_KIND.from_name(ctx.rulekind)),
            "params"
            / Switch(
                lambda ctx: ctx.kind,
                {
                    ALTIUM_RULE_KIND.CLEARANCE: Struct(
                        "clearance_gap" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("GAP", "10mil"))
                    ),
                    ALTIUM_RULE_KIND.DIFF_PAIR_ROUTINGS: Struct(),
                    ALTIUM_RULE_KIND.HEIGHT: Struct(),
                    ALTIUM_RULE_KIND.HOLE_SIZE: Struct(
                        "min_limit" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("MINLIMIT", "1mil")),
                        "max_limit" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("MAXLIMIT", "150mil")),
                    ),
                    ALTIUM_RULE_KIND.HOLE_TO_HOLE_CLEARANCE: Struct(
                        "clearance_gap" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("GAP", "10mil"))
                    ),
                    ALTIUM_RULE_KIND.ROUTING_VIAS: Struct(
                        "width" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("WIDTH", "20mil")),
                        "min_width" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("MINWIDTH", "20mil")),
                        "max_width" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("MAXWIDTH", "50mil")),
                        "hole_width" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("HOLEWIDTH", "10mil")),
                        "min_hole_width"
                        / Computed(lambda ctx: ctx._.properties.read_kicad_unit("MINHOLEWIDTH", "10mil")),
                        "max_hole_width"
                        / Computed(lambda ctx: ctx._.properties.read_kicad_unit("MAXHOLEWIDTH", "28mil")),
                    ),
                    ALTIUM_RULE_KIND.WIDTH: Struct(
                        "min_limit" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("MINLIMIT", "6mil")),
                        "max_limit" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("MAXLIMIT", "40mil")),
                        "preferred_width"
                        / Computed(lambda ctx: ctx._.properties.read_kicad_unit("PREFERREDWIDTH", "6mil")),
                    ),
                    ALTIUM_RULE_KIND.PASTE_MASK_EXPANSION: Struct(
                        "pastemask_expansion" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("EXPANSION", "0"))
                    ),
                    ALTIUM_RULE_KIND.SOLDER_MASK_EXPANSION: Struct(
                        "soldermask_expansion"
                        / Computed(lambda ctx: ctx._.properties.read_kicad_unit("EXPANSION", "4mil"))
                    ),
                    ALTIUM_RULE_KIND.PLANE_CLEARANCE: Struct(
                        "plane_clearance" / Computed(lambda ctx: ctx._.properties.read_kicad_unit("CLEARANCE", "10mil"))
                    ),
                    ALTIUM_RULE_KIND.POLYGON_CONNECT: Struct(
                        "polygon_connect_airgap_width"
                        / Computed(lambda ctx: ctx._.properties.read_kicad_unit("AIRGAPWIDTH", "10mil")),
                        "polygon_connect_relief_conductor_width"
                        / Computed(lambda ctx: ctx._.properties.read_kicad_unit("RELIEFCONDUCTORWIDTH", "10mil")),
                        "polygon_connect_relief_entries"
                        / Computed(lambda ctx: ctx._.properties.read_int("RELIEFENTRIES", 4)),
                        "polygon_connect_style"
                        / Computed(
                            lambda ctx: ALTIUM_CONNECT_STYLE.from_name(ctx._.properties.read_string("CONNECTSTYLE", ""))
                        ),
                    ),
                },
                default=Struct(),
            ),
        ),
    )
)

ConstructArcs6 = Struct(
    "arcs"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "recordtype" / ALTIUM_RECORD.as_construct(Int8ul),
            "recordlength" / Int32ul,
            "subrecord_start" / Tell,
            "layer" / ALTIUM_LAYER.as_construct(Int8ul),
            "flags1" / Int8ul,
            "is_locked" / Computed(lambda ctx: (ctx.flags1 & 0x04) == 0),
            "is_polygonoutline" / Computed(lambda ctx: (ctx.flags1 & 0x02) != 0),
            "flags2" / Int8ul,
            "is_keepout" / Computed(lambda ctx: (ctx.flags2 == 2)),
            "net" / Int16ul,
            "polygon" / Int16ul,
            "component" / Int16ul,
            "skip_4" / SKIP(4),
            "center" / POSITION(),
            "radius" / KICAD_UNIT(),
            "start_angle" / Float64l,
            "end_angle" / Float64l,
            "width" / KICAD_UNIT(),
            "subpolyindex" / Int16ul,
            # "keepoutrestrictions"
            # / IfThenElse(
            #     lambda ctx: (ctx._root._io.seek(0, 2) - ctx._root._io.tell()) >= 10,
            #     Struct("padding" / SKIP(9), "value" / Byte),
            #     Computed(lambda ctx: 0x1F if ctx.is_keepout else 0),
            # ),
            "subrecord_end" / Tell,
            "skip_remaining" / Padding(lambda ctx: ctx.recordlength - (ctx.subrecord_end - ctx.subrecord_start)),
        ),
    ),
)

ConstructComponentBodies6 = Struct(
    "recordtype" / ALTIUM_RECORD.as_construct(Int8ul),
    "recordlength" / Int32ul,
    "skip_7" / SKIP(7),
    "component" / Int16ul,
    "skip_9" / SKIP(9),
    "properties" / PROPERTIES,
    "model_name" / Computed(lambda ctx: ctx.properties.read_string("MODEL.NAME", "")),
    "model_id" / Computed(lambda ctx: ctx.properties.read_string("MODELID", "")),
    "model_is_embedded" / Computed(lambda ctx: ctx.properties.read_bool("MODEL.EMBED", False)),
    "model_position"
    / Computed(
        lambda ctx: (
            ctx.properties.read_kicad_unit("MODEL.2D.X", "0mil"),
            -ctx.properties.read_kicad_unit("MODEL.2D.Y", "0mil"),
            ctx.properties.read_kicad_unit("MODEL.3D.DZ", "0mil"),
        )
    ),
    "model_rotation"
    / Computed(
        lambda ctx: (
            ctx.properties.read_double("MODEL.3D.ROTX", 0.0),
            -ctx.properties.read_double("MODEL.3D.ROTY", 0.0),
            ctx.properties.read_double("MODEL.3D.ROTZ", 0.0),
        )
    ),
    "model_rotation" / Computed(lambda ctx: ctx.properties.read_double("MODEL.2D.ROTATION", 0.0)),
    "body_opacity_3d" / Computed(lambda ctx: ctx.properties.read_double("BODYOPACITY3D", 1.0)),
    "remainder" / GreedyBytes,
)


ConstructPads6 = Struct(
    "pads"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "recordtype" / ALTIUM_RECORD.as_construct(Int8ul),
            "subrecord1"
            / Prefixed(
                Int32ul,
                Struct(
                    "name" / WXSTRING,
                ),
            ),
            "subrecord2" / Prefixed(Int32ul, Pass),
            "subrecord3" / Prefixed(Int32ul, Pass),
            "subrecord4" / Prefixed(Int32ul, Pass),
            "subrecord5length" / Int32ul,
            "subrecord5_start" / Tell,
            "layer" / ALTIUM_LAYER.as_construct(Int8ul),
            "flags1" / Int8ul,
            "is_test_fab_top" / Computed(lambda ctx: (ctx.flags1 & 0x80) != 0),
            "is_tent_bottom" / Computed(lambda ctx: (ctx.flags1 & 0x40) != 0),
            "is_tent_top" / Computed(lambda ctx: (ctx.flags1 & 0x20) != 0),
            "is_locked" / Computed(lambda ctx: (ctx.flags1 & 0x04) == 0),
            "flags2" / Int8ul,
            "is_test_fab_bottom" / Computed(lambda ctx: (ctx.flags2 & 0x01) != 0),
            "net" / Int16ul,
            "skip_2" / SKIP(2),
            "component" / Int16ul,
            "skip_4" / SKIP(4),
            "position" / POSITION(),
            "topsize" / SIZE,
            "midsize" / SIZE,
            "botsize" / SIZE,
            "holesize" / KICAD_UNIT(),
            "topshape" / ALTIUM_PAD_SHAPE.as_construct(Int8ul),
            "midshape" / ALTIUM_PAD_SHAPE.as_construct(Int8ul),
            "botshape" / ALTIUM_PAD_SHAPE.as_construct(Int8ul),
            "direction" / Float64l,
            "plated" / Flag,
            "skip_1" / SKIP(1),
            "padmode" / ALTIUM_PAD_MODE.as_construct(Int8ul),
            "skip_23" / SKIP(23),
            "pastemaskexpansionmanual" / KICAD_UNIT(),
            "soldermaskexpansionmanual" / KICAD_UNIT(),
            "skip_7" / SKIP(7),
            "pastemaskexpansionmode" / ALTIUM_MODE.as_construct(Int8ul),
            "soldermaskexpansionmode" / ALTIUM_MODE.as_construct(Int8ul),
            "skip_3" / SKIP(3),
            "holerotation"
            / IfThenElse(
                lambda ctx: ctx.subrecord5length == 110,
                Struct(
                    "unknown" / KICAD_UNIT(),
                    "holerotation" / Computed(0),
                ),
                Struct(
                    "holerotation" / Float64l,
                ),
            ),
            "layerdata"
            / IfThenElse(
                lambda ctx: ctx.subrecord5length >= 120,
                Struct(
                    "to_layer" / ALTIUM_LAYER.as_construct(Int8ul),
                    "skip_2" / SKIP(2),
                    "from_layer" / ALTIUM_LAYER.as_construct(Int8ul),
                ),
                Pass,
            ),
            "subrecord5_end" / Tell,
            "skip_remaining" / Padding(lambda ctx: ctx.subrecord5length - (ctx.subrecord5_end - ctx.subrecord5_start)),
            "subrecord6length" / Int32ul,
            "subrecord6_start" / Tell,
            "size_and_shape"
            / IfThenElse(
                lambda ctx: ctx.subrecord6length >= 596,
                Struct(
                    "inner_size_x" / Array(29, KICAD_UNIT_X()),
                    "inner_size_y" / Array(29, KICAD_UNIT_Y()),
                    "inner_shape" / Array(29, ALTIUM_PAD_SHAPE.as_construct(Int8ul)),
                    "skip_1" / SKIP(1),
                    "holeshape" / ALTIUM_PAD_HOLE_SHAPE.as_construct(Int8sl),
                    "slotsize" / KICAD_UNIT(),
                    "slotrotation" / Float64l,
                    "holeoffset_x" / Array(29, KICAD_UNIT_X()),
                    "holeoffset_y" / Array(29, KICAD_UNIT_Y()),
                    "skip_1_2" / SKIP(1),
                    "alt_shape" / Array(32, ALTIUM_PAD_SHAPE_ALT.as_construct(Int8ul)),
                    "cornerradius" / Array(32, Int8ul),
                ),
                Pass,
            ),
            "subrecord6_end" / Tell,
            "skip_remaining" / Padding(lambda ctx: ctx.subrecord6length - (ctx.subrecord6_end - ctx.subrecord6_start)),
        ),
    )
)

ConstructVias6 = Struct(
    "vias"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "recordtype" / ALTIUM_RECORD.as_construct(Int8ul),
            "recordlength" / Int32ul,
            "subrecord_start" / Tell,
            "skip_1" / SKIP(1),
            "flags1" / Int8ul,
            "is_test_fab_top" / Computed((this.flags1 & 0x80) != 0),
            "is_tent_bottom" / Computed((this.flags1 & 0x40) != 0),
            "is_tent_top" / Computed((this.flags1 & 0x20) != 0),
            "is_locked" / Computed((this.flags1 & 0x04) == 0),
            "flags2" / Int8ul,
            "is_test_fab_bottom" / Computed((this.flags2 & 0x01) != 0),
            "net" / Int16ul,
            "skip_8" / SKIP(8),
            "position" / POSITION(),
            "diameter" / KICAD_UNIT(),
            "holesize" / KICAD_UNIT(),
            "layer_start" / ALTIUM_LAYER.as_construct(Int8ul),
            "layer_end" / ALTIUM_LAYER.as_construct(Int8ul),
            "properties"
            / IfThenElse(
                this.recordlength > 74,
                Struct(
                    "temp_byte" / Int8ul,
                    "thermal_relief_airgap" / KICAD_UNIT(),
                    "thermal_relief_conductorcount" / Int8ul,
                    "skip_1" / SKIP(1),
                    "thermal_relief_conductorwidth" / KICAD_UNIT(),
                    "skip_20mil_1" / KICAD_UNIT(),
                    "skip_20mil_2" / KICAD_UNIT(),
                    "skip_4" / SKIP(4),
                    "soldermask_expansion_front" / KICAD_UNIT(),
                    "skip_8_2" / SKIP(8),
                    "temp_byte_2" / Int8ul,
                    "soldermask_expansion_manual" / Computed(this.temp_byte_2 & 0x02),
                    "skip_7" / SKIP(7),
                    "viamode" / ALTIUM_PAD_MODE.as_construct(Int8ul),
                    "diameter_by_layer" / Array(32, KICAD_UNIT()),
                ),
                Struct(
                    "viamode" / Computed(ALTIUM_PAD_MODE.SIMPLE),
                ),
            ),
            "soldermasks"
            / IfThenElse(
                this.recordlength >= 246,
                Struct(
                    "skip_38" / SKIP(38),
                    "soldermask_expansion_linked_byte" / Byte,
                    "soldermask_expansion_linked" / Computed(this.soldermask_expansion_linked_byte & 0x01),
                    "soldermask_expansion_back" / KICAD_UNIT(),
                ),
                Pass,
            ),
            "tolerances"
            / IfThenElse(
                this.recordlength >= 307,
                Struct(
                    "skip_45" / SKIP(45),
                    "pos_tolerance" / KICAD_UNIT(),
                    "neg_tolerance" / KICAD_UNIT(),
                ),
                Pass,
            ),
            "subrecord_end" / Tell,
            "skip_remaining" / Padding(lambda ctx: ctx.recordlength - (ctx.subrecord_end - ctx.subrecord_start)),
        ),
    )
)

ConstructTracks6 = Struct(
    "tracks"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "recordtype" / ALTIUM_RECORD.as_construct(Int8ul),
            "recordlength" / Int32ul,
            "subrecord_start" / Tell,
            "layer" / ALTIUM_LAYER.as_construct(Int8ul),
            "flags1" / Byte,
            "is_locked" / Computed((this.flags1 & 0x04) != 0),
            "is_polygonoutline" / Computed((this.flags1 & 0x02) != 0),
            "flags2" / Byte,
            "is_keepout" / Computed(this.flags2 == 2),
            "net" / Int16ul,
            "polygon" / Int16ul,
            "component" / Int16ul,
            "skip_4" / SKIP(4),
            "start" / POSITION(),
            "end" / POSITION(),
            "width" / KICAD_UNIT(),
            "subpolyindex" / Int16ul,
            "properties"
            / IfThenElse(
                lambda ctx: get_remaining_bytes(ctx) >= 11,
                Struct("skip_10" / SKIP(10), "keepoutrestrictions" / Int8ul),
                Computed(lambda ctx: 0x1F if ctx.is_keepout else 0),
            ),
            "subrecord_end" / Tell,
            "skip_remaining" / Padding(lambda ctx: ctx.recordlength - (ctx.subrecord_end - ctx.subrecord_start)),
        ),
    )
)


ConstructTexts6 = Struct(
    "recordtype" / ALTIUM_RECORD.as_construct(Int8ul),
    "subrecord1_length" / Int32ul,
    "layer" / ALTIUM_LAYER.as_construct(Int8ul),
    "skip_6" / SKIP(6),
    "component" / Int16ul,
    "skip_4" / SKIP(4),
    "position" / POSITION(),
    "height" / KICAD_UNIT(),
    "strokefonttype" / STROKE_FONT_TYPE.as_construct(Int16ul),
    "rotation" / Float64l,
    "isMirrored" / Flag,
    "strokewidth" / KICAD_UNIT(),
    "fonttype"
    / IfThenElse(
        lambda ctx: ctx.subrecord1_length < 123,
        Computed(ALTIUM_TEXT_TYPE.STROKE),
        ALTIUM_TEXT_TYPE.as_construct(Int8sl),
    ),
    "isComment" / If(lambda ctx: ctx.subrecord1_length >= 123, Flag),
    "isDesignator" / If(lambda ctx: ctx.subrecord1_length >= 123, Flag),
    "skip_1" / If(lambda ctx: ctx.subrecord1_length >= 123, Bytes(1)),
    "isBold" / If(lambda ctx: ctx.subrecord1_length >= 123, Flag),
    "isItalic" / If(lambda ctx: ctx.subrecord1_length >= 123, Flag),
    "fontData" / If(lambda ctx: ctx.subrecord1_length >= 123, Bytes(64)),
    "fontname"
    / If(
        lambda ctx: ctx.subrecord1_length >= 123, Computed(lambda ctx: ctx.fontData.decode('utf-16le').split('\x00')[0])
    ),
    "tmpbyte" / If(lambda ctx: ctx.subrecord1_length >= 123, Byte),
    "isInverted"
    / Computed(lambda ctx: ctx.fonttype == 1 and (ctx.tmpbyte != 0) if ctx.subrecord1_length >= 123 else False),
    "margin_border_width" / If(lambda ctx: ctx.subrecord1_length >= 123, KICAD_UNIT()),
    "widestring_index" / If(lambda ctx: ctx.subrecord1_length >= 123, Int32ul),
    "skip_4_2" / If(lambda ctx: ctx.subrecord1_length >= 123, Bytes(4)),
    "isInvertedRect"
    / Computed(
        lambda ctx: ctx.fonttype == 1 and (ctx.subrecord1_length >= 123) if ctx.subrecord1_length >= 123 else False
    ),
    "textbox_rect_width" / If(lambda ctx: ctx.subrecord1_length >= 123, KICAD_UNIT()),
    "textbox_rect_height" / If(lambda ctx: ctx.subrecord1_length >= 123, KICAD_UNIT()),
    "textbox_rect_justification"
    / If(lambda ctx: ctx.subrecord1_length >= 123, ALTIUM_TEXT_POSITION.as_construct(Int8ul)),
    "text_offset_width" / If(lambda ctx: ctx.subrecord1_length >= 123, KICAD_UNIT()),
    "extra_fields"
    / If(
        lambda ctx: ctx.subrecord1_length >= 103,
        Struct(
            "skip_24" / Bytes(24),
            "skip_64" / Bytes(64),
            "skip_5" / Bytes(5),
            "isFrame" / Flag,
            "isOffsetBorder" / Flag,
            "skip_8" / Bytes(8),
        ),
    ),
    "isFrame"
    / If(
        lambda ctx: ctx.subrecord1_length < 103,
        Computed(lambda ctx: ctx.textbox_rect_height != 0 and ctx.textbox_rect_width != 0),
    ),
    "isOffsetBorder" / If(lambda ctx: ctx.subrecord1_length < 103, Computed(False)),
    "isJustificationValid" / IfThenElse(lambda ctx: ctx.subrecord1_length >= 115, Flag, Computed(False)),
    "subrecord2_length" / Int32ul,
    "text"
    / FixedSized(
        this.subrecord2_length,
        Computed(lambda ctx: ctx._io.read(ctx.subrecord2_length).decode('utf-8', errors='replace')),
    ),
)


ConstructFills6 = Struct(
    "fills"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "recordtype" / ALTIUM_RECORD.as_construct(Int8ul),
            "recordlength" / Int32ul,
            "subrecord_start" / Tell,
            "layer" / ALTIUM_LAYER.as_construct(Int8ul),
            "flags1" / Byte,
            "is_locked" / Computed(lambda ctx: (ctx.flags1 & 0x04) != 0),
            "flags2" / Int8ul,
            "is_keepout" / Computed(lambda ctx: ctx.flags2 == 2),
            "net" / Int16ul,
            "skip_2" / SKIP(2),
            "component" / Int16ul,
            "skip_4" / SKIP(4),
            "pos1" / POSITION(),
            "pos2" / POSITION(),
            "rotation" / Float64l,
            "keepoutrestrictions"
            / IfThenElse(
                lambda ctx: get_remaining_bytes(ctx) >= 10,
                Struct(
                    "skip_9" / SKIP(9),
                    "value" / Byte,
                ),
                Struct("value" / Computed(lambda ctx: 0x1F if ctx.is_keepout else 0)),
            ),
            "subrecord_end" / Tell,
            "skip_remaining" / Padding(lambda ctx: ctx.recordlength - (ctx.subrecord_end - ctx.subrecord_start)),
        ),
    )
)


ConstructClasses6 = Struct(
    "classes"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "properties" / PROPERTIES,
            "name" / Computed(lambda ctx: ctx.properties.read_string("NAME", "")),
            "unique_id" / Computed(lambda ctx: ctx.properties.read_string("UNIQUEID", "")),
            "kind" / Computed(lambda ctx: ctx.properties.read_int("KIND", -1)),
            "names" / Computed(lambda ctx: ctx.properties.read_class_names()),
        ),
    )
)

ConstructRegions6 = lambda extendedvert: Struct(
    "regions"
    / RepeatUntil(
        lambda obj, lst, ctx: get_remaining_bytes(ctx) < 4,
        Struct(
            "recordtype" / ALTIUM_RECORD.as_construct(Int8ul),
            "recordlength" / Int32ul,
            "subrecord_start" / Tell,
            "layer" / ALTIUM_LAYER.as_construct(Int8ul),
            "flags1" / Byte,
            "is_locked" / Computed(lambda ctx: (ctx.flags1 & 0x04) == 0),
            "flags2" / Byte,
            "is_keepout" / Computed(lambda ctx: (ctx.flags2 == 2)),
            "net" / Int16ul,
            "polygon" / Int16ul,
            "component" / Int16ul,
            "skip_5" / Bytes(5),
            "holecount" / Int16ul,
            "skipt_2" / Bytes(2),
            "properties" / PROPERTIES,
            "pkind" / Computed(lambda ctx: ctx.properties.read_int("KIND", 0)),
            "is_cutout" / Computed(lambda ctx: ctx.properties.read_bool("ISBOARDCUTOUT", False)),
            "is_shapebased" / Computed(lambda ctx: ctx.properties.read_bool("ISSHAPEBASED", False)),
            "keepoutrestrictions" / Computed(lambda ctx: ctx.properties.read_int("KEEPOUTRESTRIC", 0x1F)),
            "subpolyindex" / Computed(lambda ctx: ctx.properties.read_int("SUBPOLYINDEX", (2**16) - 1)),
            "kind" / Computed(lambda ctx: ctx.pkind),
            "num_outline_vertices" / Int32ul,
            "num_vertices" / Computed(lambda ctx: ctx.num_outline_vertices + (1 if extendedvert else 0)),
            "outline"
            / Array(
                this.num_vertices,
                IfThenElse(
                    extendedvert,
                    Struct(
                        "is_round" / Byte,
                        "position" / POSITION(),
                        "center" / POSITION(),
                        "radius" / KICAD_UNIT(),
                        "start_angle" / Float64l,
                        "end_angle" / Float64l,
                    ),
                    Struct("position" / POSITION(Float64l)),
                ),
            ),
            "holes"
            / Array(
                this.holecount,
                Struct(
                    "num_hole_vertices" / Int32ul,
                    "vertices"
                    / Array(
                        this.num_hole_vertices,
                        Struct(
                            "x" / KICAD_UNIT_X(Float64l),
                            "y" / KICAD_UNIT_X(Float64l),
                        ),
                    ),
                ),
            ),
            "subrecord_end" / Tell,
            "skip_remaining" / Padding(lambda ctx: ctx.recordlength - (ctx.subrecord_end - ctx.subrecord_start)),
        ),
    )
)
