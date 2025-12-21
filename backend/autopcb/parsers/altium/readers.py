import locale
import logging
from dataclasses import dataclass
from typing import Dict, List

from kicad_modification.datatypes import Position
from kicad_modification.parsers.altium.converters import (
    convert_property_to_kicad_string,
    convert_to_kicad_unit,
    format_internal_units,
)


@dataclass
class AltiumLayer:
    name: str
    next_id: int
    prev_id: int
    copperthick: int
    dielectricconst: float
    dielectricthick: int
    dielectricmaterial: str


@dataclass
class AltiumVertex:
    is_round: bool
    radius: int
    start_angle: float
    end_angle: float
    position: Position
    center: Position


class AltiumPropertyReader:
    """
    Class to postprocess property field read from Altium binary to make parsing to KiCAD easier.
    """

    def __init__(self, length: int, data: bytes):
        """Initialize a property dictionary obtained by extracting bytes from the stream"""
        self.props = self.read_properties(length, data)

    def read_properties(self, length: int, data: bytes) -> Dict[str, str]:
        """
        Parses a sequence of properties from a KiCAD binary-encoded data stream.
        """
        kv = {}
        length &= 0x00FFFFFF

        if length == 0:
            return kv

        has_null_byte = data[-1] == 0
        str_data = data[: length - (1 if has_null_byte else 0)].decode('latin1')
        position = 0

        while position < len(str_data):
            if str_data[position] == '|':
                position += 1

            token_equal = str_data.find('=', position)
            if token_equal == -1:
                break

            key_start = position
            key = str_data[key_start:token_equal].strip().upper()
            token_end = str_data.find('|', token_equal)
            if token_end == -1:
                token_end = len(str_data)

            value_start = token_equal + 1
            value_end = token_end
            value = str_data[value_start:value_end]

            if key.startswith('%UTF8%'):
                key = key[len('%UTF8%') :].strip().upper()
                value = value.encode('latin1').decode('utf-8')

            value = value.replace("ÿ", " ") if key not in ('PATTERN', 'SOURCEFOOTPRINTLIBRARY') else value

            if key in ('DESIGNATOR', 'NAME', 'TEXT'):
                value = convert_property_to_kicad_string(value.strip())
            else:
                value = value.strip()

            kv[key] = value
            position = token_end

        return kv

    def read_int(self, key: str, default: int) -> int:
        """
        Retrieves an integer property from the properties.
        """
        value = self.props.get(key)
        return default if value is None else int(value)

    def read_double(self, key: str, default: float) -> float:
        """
        Retrieves a floating-point property from the properties.
        """
        value = self.props.get(key)
        if value is None:
            return default

        try:
            return locale.atof(value)
        except ValueError:
            logging.debug(f"Unable to convert '{value}' to double.")
            return default

    def read_bool(self, key: str, default: bool) -> bool:
        """
        Retrieves a boolean property from the properties.
        """
        value = self.props.get(key)
        return value in ("T", "TRUE") if value is not None else default

    def read_kicad_unit(self, key: str, default: str) -> int:
        """
        Retrieves a KiCAD unit value from the properties.
        """
        value = self.read_string(key, default)
        if not value.endswith("mil"):
            logging.debug(f"Unit '{value}' does not end with 'mil'.")
            return 0

        prefix = value[:-3]
        try:
            mils = float(prefix)
            return format_internal_units(convert_to_kicad_unit(mils * 10000))
        except ValueError:
            logging.debug(f"Cannot convert '{prefix}' to double.")
            return 0

    def read_string(self, key: str, default: str) -> str:
        """
        Retrieves a string property from the properties.
        """
        utf8_key = "%UTF8%" + key
        return self.props.get(utf8_key, self.props.get(key, default))

    def read_unicode_string(self, key: str, default: str) -> str:
        """
        Retrieves a Unicode string property from the properties.
        """
        if "EXISTS" in self.props.get("UNICODE", ""):
            unicode_key = "UNICODE__" + key
            unicode_value = self.props.get(unicode_key)
            if unicode_value:
                return ''.join(chr(int(part)) for part in unicode_value.split(","))
        return self.read_string(key, default)

    def read_layer_stackup(self) -> List[AltiumLayer]:
        """
        Parses the layer stackup configuration from properties.
        """
        stackup = []
        layer_names = set()
        i = 1
        while i < len(self.props):
            layer_name_key = f"LAYER{i}NAME"
            if layer_name_key not in self.props:
                break
            name = self.read_string(layer_name_key, "")
            original_name = name
            ii = 2
            while name in layer_names:
                name = f"{original_name} {ii}"
                ii += 1
            layer_names.add(name)

            layer = AltiumLayer(
                name=name,
                next_id=self.read_int(f"LAYER{i}NEXT", 0),
                prev_id=self.read_int(f"LAYER{i}PREV", 0),
                copperthick=self.read_kicad_unit(f"LAYER{i}COPTHICK", "1.4mil"),
                dielectricconst=self.read_double(f"LAYER{i}DIELCONST", 0.0),
                dielectricthick=self.read_kicad_unit(f"LAYER{i}DIELHEIGHT", "60mil"),
                dielectricmaterial=self.read_string(f"LAYER{i}DIELMATERIAL", "FR-4"),
            )
            stackup.append(layer)
            i += 1

        return stackup

    def read_board_polygons(self) -> List[AltiumVertex]:
        """
        Parses board polygon vertices from properties.
        """
        vertices = []
        i = 0
        while True:
            si = str(i)
            vxi = f"VX{si}"
            vyi = f"VY{si}"
            if vxi not in self.props or vyi not in self.props:
                break
            vertex = AltiumVertex(
                is_round=self.read_int(f"KIND{si}", 0) != 0,
                radius=self.read_kicad_unit(f"R{si}", "0mil"),
                start_angle=self.read_double(f"SA{si}", 0.0),
                end_angle=self.read_double(f"EA{si}", 0.0),
                position=Position(self.read_kicad_unit(vxi, "0mil"), -self.read_kicad_unit(vyi, "0mil")),
                center=Position(self.read_kicad_unit(f"CX{si}", "0mil"), -self.read_kicad_unit(f"CY{si}", "0mil")),
            )
            vertices.append(vertex)
            i += 1
        return vertices

    def read_class_names(self) -> List[str]:
        """
        Extracts class names from properties.
        """
        return [value for key, value in self.props.items() if key.startswith("M") and key[1:].isdigit()]

    def read_text_points(self) -> List[Position]:
        """
        Extracts text points from properties
        """
        text_points = []
        i = 1
        while True:
            x_key = f"TEXT{i}X"
            y_key = f"TEXT{i}Y"
            if not x_key in self.props or not y_key in self.props:
                break
            x = self.read_kicad_unit(x_key, "0mil")
            y = -self.read_kicad_unit(y_key, "0mil")
            text_points.append(Position(x, y))
            i += 1

        return text_points
