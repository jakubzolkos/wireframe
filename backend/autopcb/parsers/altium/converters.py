import inspect
import math
import sys
from typing import Type

from construct import Container
from kicad_modification.datatypes import Position


def ki_round(value: float, ret_type: Type[int | float] = int, quiet: bool = False) -> int | float:
    """
    Python equivalent of KiROUND, rounding a float to the nearest value of a specified type.

    Args:
        value (float): The input value to round.
        ret_type (Type): The type to round to (e.g., int or float). Defaults to int.
        quiet (bool): If False, logs overflow cases. Defaults to False.

    Returns:
        int | float: The rounded value, clamped to the range of ret_type if necessary.
    """
    # Compute the rounded value
    rounded = math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)

    # Define type limits for overflow handling
    if ret_type is int:
        type_min, type_max = -(2**31), 2**31 - 1
    elif ret_type is float:
        type_min, type_max = -sys.float_info.max, sys.float_info.max
    else:
        raise ValueError("Unsupported ret_type. Only int and float are supported.")

    # Overflow handling
    if rounded > type_max:
        if not quiet:
            print(f"Overflow: {value} exceeds maximum {ret_type.__name__} value.")
        return type_max - 1
    elif rounded < type_min:
        if not quiet:
            print(f"Overflow: {value} is less than minimum {ret_type.__name__} value.")
        return type_min + 1 if ret_type is int and type_min < 0 else 0

    # NaN handling
    if math.isnan(value):
        if not quiet:
            print(f"NaN detected: {value} is not a valid number.")
        return 0

    return ret_type(rounded)


def format_internal_units(value: int, iu_per_mm: float = 1e6) -> float:
    eng_units = value / iu_per_mm

    if eng_units != 0.0 and abs(eng_units) <= 0.0001:
        # Round to 10 decimal places
        eng_units = round(eng_units, 10)
    else:
        # Use general format for floating point
        eng_units = float(f"{eng_units:.10g}")

    return eng_units


def convert_to_kicad_unit(a_value: int) -> int:
    """Altium stores data in mils while KiCAD required milimeters"""

    def clamp(value, min_value, max_value):
        return max(min(value, max_value), min_value)

    int_limit = (2**31 - 1 - 10) / 2.54
    iu = ki_round(clamp(a_value, -int_limit, int_limit) * 2.54)

    # Altium's internal precision is 0.1uinch.  KiCad's is 1nm.  Round to nearest 10nm to clean
    # up most rounding errors.  This allows lossless conversion of increments of 0.05mils and
    # 0.01um.
    return ki_round(iu / 10.0) * 10


def convert_property_to_kicad_string(a_string: str):
    """Sanitizes an Altium property"""
    converted = ""
    in_overbar = False
    iterator = iter(range(len(a_string)))

    for i in iterator:
        char = a_string[i]
        lookahead = a_string[i + 1] if i + 1 < len(a_string) else None

        if lookahead == '\\':
            if not in_overbar:
                converted += "~{"
                in_overbar = True

            converted += char
            next(iterator)
        else:
            if in_overbar:
                converted += "}"
                in_overbar = False

            converted += char

    if in_overbar:
        converted += "}"

    return converted


def convert_altium_position(altium_position: Container) -> Position:
    """Converts an Altium position construct to Python"""
    if hasattr(altium_position, "x") and hasattr(altium_position, "y"):
        return Position(altium_position.x, altium_position.y)
    else:
        raise AttributeError("Invalid Altium position.")


def convert_object(source, target_cls):
    """
    Converts an object of one class to another by copying overlapping attributes. Used to go between Fp and Gr items.

    Args:
        source: The source object to convert from.
        target_cls: The target class to create an instance of.

    Returns:
        An instance of the target class with overlapping attributes copied from the source.
    """
    source_attrs = {
        name: getattr(source, name)
        for name in dir(source)
        if not name.startswith("__") and not callable(getattr(source, name))
    }

    target_instance = target_cls()
    for attr, value in source_attrs.items():
        if hasattr(target_instance, attr):
            setattr(target_instance, attr, value)

    return target_instance
