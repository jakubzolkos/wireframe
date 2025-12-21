from autopcb.datatypes.schematics import (
    LibSymbol, SchProperty, Pin, PinName, PinNumber, PinNames, PinNumbers,
    Polyline, SchFreeformText, SchFont, SchEffects, SchStroke, Fill,
    SchShapeLineChain, SymbolUnit
)
from autopcb.datatypes.pcb import (
    Layer, LayerList, BoardStackup, BoardStackupItem, BoardStackupItemThickness,
    PcbPlotParams, DimensionDefaults, Defaults, Setup, General, PageInfo, Net, Board,
    FpText, Effects, Font, Stroke
)
from autopcb.datatypes.common import Vector2D, Vector2DWithRotation


def PowerSymbol(reference: str) -> LibSymbol:
    """Creates a VCC power symbol"""
    power_symbol = LibSymbol(
        name="VCC",
        power=None,
        body_styles=None,
        pin_numbers=PinNumbers(hide=True),
        pin_names=PinNames(offset=None, hide=True),
        exclude_from_sim=None,
        in_bom=True,
        on_board=True,
        duplicate_pin_numbers_are_jumpers=None,
        jumper_pin_groups=[],
        properties=[
            SchProperty(
                name="Reference",
                value="#PWR",
                private=False,
                id=0,
                at=Vector2DWithRotation(x=0, y=-3.81, rot=0),
                hide=None,
                effects=None,
                show_name=None,
                do_not_autoplace=None
            ),
            SchProperty(
                name="Value",
                value="VCC",
                private=False,
                id=1,
                at=Vector2DWithRotation(x=0, y=3.556, rot=0),
                hide=None,
                effects=None,
                show_name=None,
                do_not_autoplace=None
            ),
        ],
        extends=None,
        symbols=[],
        embedded_fonts=None,
        embedded_files=[]
    )

    # Create unit 0 (graphical representation) - triangle pointing up
    unit0_polylines = [
        # Left side of triangle
        Polyline(
            private=False,
            pts=SchShapeLineChain(xys=[
                Vector2D(x=-0.762, y=1.27),
                Vector2D(x=0, y=2.54)
            ]),
            stroke=SchStroke(width=0, type="default", color=None),
            fill=Fill(type="none", color=None)
        ),
        # Right side of triangle
        Polyline(
            private=False,
            pts=SchShapeLineChain(xys=[
                Vector2D(x=0, y=2.54),
                Vector2D(x=0.762, y=1.27)
            ]),
            stroke=SchStroke(width=0, type="default", color=None),
            fill=Fill(type="none", color=None)
        ),
        # Vertical line
        Polyline(
            private=False,
            pts=SchShapeLineChain(xys=[
                Vector2D(x=0, y=0),
                Vector2D(x=0, y=2.54)
            ]),
            stroke=SchStroke(width=0, type="default", color=None),
            fill=Fill(type="none", color=None)
        )
    ]

    unit0 = SymbolUnit(
        name="VCC_0_1",
        unit_name=None,
        polylines=unit0_polylines,
        arcs=[],
        beziers=[],
        circles=[],
        rectangles=[],
        texts=[],
        text_boxes=[],
        pins=[],
        _unit=0,
        _variant=1
    )

    # Create unit 1 (pin)
    unit1_pin = Pin(
        type="power_in",
        shape="line",
        at=Vector2DWithRotation(x=0, y=0, rot=90),
        length=0,
        hide=False,
        name=PinName(name="1", effects=SchEffects(font=None, justifies=[], href=None, hide=True)),
        number=PinNumber(number="1", effects=SchEffects(font=None, justifies=[], href=None, hide=True)),
        alternates=[],
        uuid=None
    )

    unit1 = SymbolUnit(
        name="VCC_1_1",
        unit_name=None,
        polylines=[],
        arcs=[],
        beziers=[],
        circles=[],
        rectangles=[],
        texts=[],
        text_boxes=[],
        pins=[unit1_pin],
        _unit=1,
        _variant=1
    )

    power_symbol.symbols = [unit0, unit1]

    return power_symbol


def GNDSymbol(reference: str) -> LibSymbol:
    """Creates an Earth ground symbol"""
    ground_symbol = LibSymbol(
        name="GND",
        power=None,
        body_styles=None,
        pin_numbers=PinNumbers(hide=True),
        pin_names=PinNames(offset=None, hide=True),
        exclude_from_sim=None,
        in_bom=True,
        on_board=True,
        duplicate_pin_numbers_are_jumpers=None,
        jumper_pin_groups=[],
        properties=[
            SchProperty(
                name="Reference",
                value="#PWR",
                private=False,
                id=0,
                at=Vector2DWithRotation(x=0, y=-6.35, rot=0),
                hide=None,
                effects=None,
                show_name=None,
                do_not_autoplace=None
            ),
            SchProperty(
                name="Value",
                value="GND",
                private=False,
                id=1,
                at=Vector2DWithRotation(x=0, y=-3.81, rot=0),
                hide=None,
                effects=None,
                show_name=None,
                do_not_autoplace=None
            ),
        ],
        extends=None,
        symbols=[],
        embedded_fonts=None,
        embedded_files=[]
    )

    # Create unit 0 (graphical representation) - ground symbol with horizontal lines
    unit0_polylines = [
        # Top horizontal line
        Polyline(
            private=False,
            pts=SchShapeLineChain(xys=[
                Vector2D(x=-0.635, y=-1.905),
                Vector2D(x=0.635, y=-1.905)
            ]),
            stroke=SchStroke(width=0, type="default", color=None),
            fill=Fill(type="none", color=None)
        ),
        # Middle horizontal line
        Polyline(
            private=False,
            pts=SchShapeLineChain(xys=[
                Vector2D(x=-0.127, y=-2.54),
                Vector2D(x=0.127, y=-2.54)
            ]),
            stroke=SchStroke(width=0, type="default", color=None),
            fill=Fill(type="none", color=None)
        ),
        # Vertical line
        Polyline(
            private=False,
            pts=SchShapeLineChain(xys=[
                Vector2D(x=0, y=-1.27),
                Vector2D(x=0, y=0)
            ]),
            stroke=SchStroke(width=0, type="default", color=None),
            fill=Fill(type="none", color=None)
        ),
        # Bottom horizontal line
        Polyline(
            private=False,
            pts=SchShapeLineChain(xys=[
                Vector2D(x=1.27, y=-1.27),
                Vector2D(x=-1.27, y=-1.27)
            ]),
            stroke=SchStroke(width=0, type="default", color=None),
            fill=Fill(type="none", color=None)
        )
    ]

    unit0 = SymbolUnit(
        name="GND_0_1",
        unit_name=None,
        polylines=unit0_polylines,
        arcs=[],
        beziers=[],
        circles=[],
        rectangles=[],
        texts=[],
        text_boxes=[],
        pins=[],
        _unit=0,
        _variant=1
    )

    # Create unit 1 (pin)
    unit1_pin = Pin(
        type="power_in",
        shape="line",
        at=Vector2DWithRotation(x=0, y=0, rot=270),
        length=0,
        hide=False,
        name=PinName(name="1", effects=SchEffects(font=None, justifies=[], href=None, hide=True)),
        number=PinNumber(number="1", effects=SchEffects(font=None, justifies=[], href=None, hide=True)),
        alternates=[],
        uuid=None
    )

    unit1 = SymbolUnit(
        name="GND_1_1",
        unit_name=None,
        polylines=[],
        arcs=[],
        beziers=[],
        circles=[],
        rectangles=[],
        texts=[],
        text_boxes=[],
        pins=[unit1_pin],
        _unit=1,
        _variant=1
    )

    ground_symbol.symbols = [unit0, unit1]

    return ground_symbol


def NoConnectSymbol(reference: str) -> LibSymbol:
    """Creates a no connect symbol (X mark)"""
    no_connect_symbol = LibSymbol(
        name="NC",
        power=None,
        body_styles=None,
        pin_numbers=PinNumbers(hide=True),
        pin_names=PinNames(offset=None, hide=True),
        exclude_from_sim=None,
        in_bom=False,
        on_board=False,
        duplicate_pin_numbers_are_jumpers=None,
        jumper_pin_groups=[],
        properties=[
            SchProperty(
                name="Reference",
                value=reference,
                private=False,
                id=0,
                at=Vector2DWithRotation(x=0, y=0, rot=0),
                hide=None,
                effects=None,
                show_name=None,
                do_not_autoplace=None
            ),
            SchProperty(
                name="Value",
                value="No Connect",
                private=False,
                id=1,
                at=Vector2DWithRotation(x=0, y=0, rot=0),
                hide=None,
                effects=None,
                show_name=None,
                do_not_autoplace=None
            ),
        ],
        extends=None,
        symbols=[],
        embedded_fonts=None,
        embedded_files=[]
    )

    # Create X mark using polylines
    polylines = [
        # First diagonal line (top-left to bottom-right)
        Polyline(
            private=False,
            pts=SchShapeLineChain(xys=[
                Vector2D(x=-0.762, y=-0.762),
                Vector2D(x=0.762, y=0.762)
            ]),
            stroke=SchStroke(width=1, type="default", color=None),
            fill=Fill(type="none", color=None)
        ),
        # Second diagonal line (top-right to bottom-left)
        Polyline(
            private=False,
            pts=SchShapeLineChain(xys=[
                Vector2D(x=-0.762, y=0.762),
                Vector2D(x=0.762, y=-0.762)
            ]),
            stroke=SchStroke(width=1, type="default", color=None),
            fill=Fill(type="none", color=None)
        )
    ]

    # Create pin
    pin = Pin(
        type="no_connect",
        shape="line",
        at=Vector2DWithRotation(x=0, y=0, rot=0),
        length=0,
        hide=False,
        name=PinName(name="1", effects=SchEffects(font=None, justifies=[], href=None, hide=True)),
        number=PinNumber(number="1", effects=SchEffects(font=None, justifies=[], href=None, hide=True)),
        alternates=[],
        uuid=None
    )

    unit = SymbolUnit(
        name="NC_1_1",
        unit_name=None,
        polylines=polylines,
        arcs=[],
        beziers=[],
        circles=[],
        rectangles=[],
        texts=[],
        text_boxes=[],
        pins=[pin],
        _unit=1,
        _variant=1
    )

    no_connect_symbol.symbols = [unit]

    return no_connect_symbol


def NetLabelSymbol(net: str) -> LibSymbol:
    """Creates a net label symbol with the specified net name"""
    net_label_symbol = LibSymbol(
        name=f"NET_LABEL_{net}",
        power=None,
        body_styles=None,
        pin_numbers=PinNumbers(hide=True),
        pin_names=PinNames(offset=None, hide=True),
        exclude_from_sim=None,
        in_bom=False,
        on_board=False,
        duplicate_pin_numbers_are_jumpers=None,
        jumper_pin_groups=[],
        properties=[
            SchProperty(
                name="Reference",
                value="NL",
                private=False,
                id=0,
                at=Vector2DWithRotation(x=0, y=0, rot=0),
                hide=None,
                effects=None,
                show_name=None,
                do_not_autoplace=None
            ),
            SchProperty(
                name="Value",
                value=net,
                private=False,
                id=1,
                at=Vector2DWithRotation(x=0, y=0, rot=0),
                hide=None,
                effects=None,
                show_name=None,
                do_not_autoplace=None
            ),
        ],
        extends=None,
        symbols=[],
        embedded_fonts=None,
        embedded_files=[]
    )

    # Create text element for the net name
    text = SchFreeformText(
        text=net,
        private=False,
        at=Vector2DWithRotation(x=0, y=1.27, rot=0),
        effects=SchEffects(
            font=SchFont(
                face=None,
                size=Vector2D(x=5, y=5),
                thickness=None,
                bold=None,
                italic=None,
                color=None,
                line_spacing=None
            ),
            justifies=["center", "center"],
            href=None,
            hide=False
        )
    )

    # Create pin
    pin = Pin(
        type="passive",
        shape="line",
        at=Vector2DWithRotation(x=0, y=0, rot=270),
        length=0,
        hide=False,
        name=PinName(name="1", effects=SchEffects(font=None, justifies=[], href=None, hide=True)),
        number=PinNumber(number="1", effects=SchEffects(font=None, justifies=[], href=None, hide=True)),
        alternates=[],
        uuid=None
    )

    unit = SymbolUnit(
        name=f"NET_LABEL_{net}_1_1",
        unit_name=None,
        polylines=[],
        arcs=[],
        beziers=[],
        circles=[],
        rectangles=[],
        texts=[text],
        text_boxes=[],
        pins=[pin],
        _unit=1,
        _variant=1
    )

    net_label_symbol.symbols = [unit]

    return net_label_symbol


def DefaultBoard() -> Board:
    """Creates an empty PCB with default settings that match KiCAD's new board defaults"""
    return Board(
        version=20240108,  # KiCAD 8.0 format version
        generator="autopcb",
        generator_version=None,
        general=General(thickness=1.6, legacy_teardrops=None),
        paper=PageInfo(type="A4", width=None, height=None, portrait=False),
        title_block=None,
        layers=[LayerList(layer_infos=[
            Layer(index=0, name="F.Cu", type="signal", user_name=None),
            Layer(index=31, name="B.Cu", type="signal", user_name=None),
            Layer(index=32, name="B.Adhes", type="user", user_name="B.Adhesive"),
            Layer(index=33, name="F.Adhes", type="user", user_name="F.Adhesive"),
            Layer(index=34, name="B.Paste", type="user", user_name=None),
            Layer(index=35, name="F.Paste", type="user", user_name=None),
            Layer(index=36, name="B.SilkS", type="user", user_name="B.Silkscreen"),
            Layer(index=37, name="F.SilkS", type="user", user_name="F.Silkscreen"),
            Layer(index=38, name="B.Mask", type="user", user_name=None),
            Layer(index=39, name="F.Mask", type="user", user_name=None),
            Layer(index=40, name="Dwgs.User", type="user", user_name="User.Drawings"),
            Layer(index=41, name="Cmts.User", type="user", user_name="User.Comments"),
            Layer(index=42, name="Eco1.User", type="user", user_name="User.Eco1"),
            Layer(index=43, name="Eco2.User", type="user", user_name="User.Eco2"),
            Layer(index=44, name="Edge.Cuts", type="user", user_name=None),
            Layer(index=45, name="Margin", type="user", user_name=None),
            Layer(index=46, name="B.CrtYd", type="user", user_name="B.Courtyard"),
            Layer(index=47, name="F.CrtYd", type="user", user_name="F.Courtyard"),
            Layer(index=48, name="B.Fab", type="user", user_name=None),
            Layer(index=49, name="F.Fab", type="user", user_name=None),
            Layer(index=50, name="User.1", type="user", user_name=None),
            Layer(index=51, name="User.2", type="user", user_name=None),
            Layer(index=52, name="User.3", type="user", user_name=None),
            Layer(index=53, name="User.4", type="user", user_name=None),
            Layer(index=54, name="User.5", type="user", user_name=None),
            Layer(index=55, name="User.6", type="user", user_name=None),
            Layer(index=56, name="User.7", type="user", user_name=None),
            Layer(index=57, name="User.8", type="user", user_name=None),
            Layer(index=58, name="User.9", type="user", user_name=None),
        ])],
        setup=Setup(
            stackup=BoardStackup(
                layer_=[],
                copper_finish=None,
                dielectric_constraints=True,
                edge_connector=None,
                edge_plating=None
            ),
            last_trace_width=None,
            user_trace_width=[],
            trace_clearance=0.2,
            zone_clearance=0.5,
            zone_45_only=False,
            clearance_min=None,
            trace_min=0.2,
            via_size=0.8,
            via_drill=0.4,
            via_min_annulus=None,
            via_min_size=0.4,
            through_hole_min=0.3,
            uvia_size=0.3,
            uvia_drill=0.1,
            uvias_allowed=False,
            blind_buried_vias_allowed=False,
            uvia_min_size=0.2,
            uvia_min_drill=0.1,
            user_diff_pair=[],
            pad_size=Vector2D(x=1.524, y=1.524),
            pad_drill=0.762,
            pad_to_mask_clearance=0.0,
            solder_mask_min_width=None,
            pad_to_paste_clearance=0.0,
            pad_to_paste_clearance_ratio=-0.0,
            allow_soldermask_bridges_in_footprints=False,
            tentings=[],
            covering=[],
            plugging=[],
            capping=None,
            filling=None,
            aux_axis_origin=None,
            grid_origin=None,
            visible_elements=None,
            max_error=0.005,
            filled_areas_thickness=False,
            defaults=None,
            pcbplotparams=PcbPlotParams(
                layerselection="0x00010fc_ffffffff",
                plot_on_all_layers_selection="0x0000000_00000000",
                disableapertmacros=False,
                usegerberextensions=False,
                usegerberattributes=True,
                usegerberadvancedattributes=True,
                creategerberjobfile=True,
                gerberprecision=6,
                dashed_line_dash_ratio=12.0,
                dashed_line_gap_ratio=3.0,
                svgprecision=4,
                svguseinch=False,
                plotframeref=False,
                mode=1,
                useauxorigin=False,
                hpglpennumber=1,
                hpglpenspeed=20,
                hpglpenoverlay=2,
                hpglpendiameter=15.0,
                pdf_front_fp_property_popups=True,
                pdf_back_fp_property_popups=True,
                pdf_metadata=True,
                pdf_single_document=False,
                dxfpolygonmode=True,
                dxfimperialunits=True,
                dxfusepcbnewfont=True,
                psnegative=False,
                psa4output=False,
                pscolor=None,
                excludeedgelayer=True,
                viasonmask=False,
                plot_black_and_white=False,
                plotinvisibletext=False,
                sketchpadsonfab=False,
                plotpadnumbers=False,
                hidednponfab=True,
                sketchdnponfab=False,
                crossoutdnponfab=True,
                subtractmaskfromsilk=False,
                outputformat=1,
                mirror=False,
                drillshape=1,
                scaleselection=1,
                outputdirectory=""
            ),
            zone_defaults=None
        ),
        properties=[],
        nets=[Net(number=0, name="")],  # Net 0 is always the default unconnected net
        net_classes=[],
        images=[],
        tables=[],
        footprints=[],
        generated=[],
        targets=[],
        gr_arcs=[],
        gr_circles=[],
        gr_curves=[],
        gr_rects=[],
        gr_bboxs=[],
        gr_lines=[],
        gr_vectors=[],
        gr_polys=[],
        gr_texts=[],
        gr_text_boxes=[],
        segments=[],
        vias=[],
        arcs=[],
        dimensions=[],
        zones=[],
        groups=[],
        embedded_fonts=None,
        embedded_files=None
    )


def DefaultFpText(text: str = "REF**", layer: str = "F.SilkS") -> FpText:
    """Creates a default FpText object for footprint reference text"""
    return FpText(
        type="reference",
        text=text,
        locked=None,
        at=Vector2DWithRotation(x=0, y=0, rot=0),
        stroke=None,
        unlocked=None,
        layer=layer,
        knockout=None,
        hide=None,
        uuid=None,
        effects=Effects(
            font=Font(
                face=None,
                size=Vector2D(x=1.0, y=1.0),
                line_spacing=None,
                thickness=0.15,
                bold=None,
                italic=None
            ),
            justifies=[],
            hide=None
        ),
        render_cache=None,
        tstamp=None
    )
