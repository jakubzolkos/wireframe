import collections
from dataclasses import dataclass
import typing
from typing import List, Union
import sys
import json
import sys
import inspect
import libcst as cst
import math
from typing import List, Tuple
import uuid
 
from autopcb.exceptions import UserFeedback


@dataclass(kw_only=True)
class HTTPResponse:
    status_code: int
    content: str


Positions = collections.namedtuple(
    'Positions',
    [
        'lineno',
        'end_lineno',
        'col_offset',
        'end_col_offset',
    ],
    defaults=[None] * 4,
)

    
def is_optional_field(data_field):
    """Checks whether a field is optional for a dataclass"""
    return typing.get_origin(data_field) is Union and type(None) in typing.get_args(data_field)


def is_close_to_int(x: float, eps: float = 1e-12) -> bool:
    return abs(x - round(x)) < eps


def generate_alphabetical_suffix(node: int):
    """Generates an alphabetical identifier based on numerical index. Use to identifysymbol units"""
    res = []
    while node > 0:
        node -= 1
        res.append(chr(node % 26 + ord('A')))
        node //= 26
    return ''.join(reversed(res))


def kicad_to_autopcb_units(x: float | int):
    # kicad stores positions in mm, but most symbols are aligned to inch grid
    # convert from mm to units of 50 mils
    x = x / (2.54 / 2)
    if not is_close_to_int(x):
        print(f'Coordinate is not near grid spacing: {x}', file=sys.stderr)
    return round(x)

    
def generate_subcircuit_suffix(node: int):
    """Generates a subcircuit identifier for footprint reference suffix from node index"""
    res = []
    while node > 0:
        node -= 1
        res.append(chr(node % 26 + ord('A')))
        node //= 26
    return ''.join(reversed(res))


def generate_footprint_uuid(footprint_ref: str, copied_subcircuit_id: str) -> str:
    """Generates a reproducible UUID given footprint reference and copied subcircuit ID"""
    namespace = uuid.NAMESPACE_DNS
    identifier = f"{footprint_ref}_{copied_subcircuit_id}"
    reproducible_uuid = str(uuid.uuid5(namespace, identifier))

    return reproducible_uuid


def pin_range(ranges: List[Tuple]):
    """Example: ranges = [(14,23),(24,27),(38,41)]"""
    pins = []
    for a_range in ranges:
        # Include +1 so the range is inclusive
        pins += [str(pin) for pin in range(a_range[0], a_range[1] + 1)]  
    return pins


api_url = "http://localhost:8000"


def http_request(verb: str, path: str, body_json_str: str = None) -> HTTPResponse:
    # when running with pyodide, this will be changed by the frontend to use the api URL base from Ian's typescript file

    if "pyodide" in sys.modules:
        # running in Pyodide
        # Use the provided js library
        import js

        xhr = js.XMLHttpRequest.new()
        # Open a synchronous ("false" for async flag) POST request to the desired URL
        xhr.open(verb.upper(), f"{api_url}{path}", False)

        if body_json_str:
            xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8")
            xhr.send(json.dumps(body_json_str))
        else:
            xhr.send()

        return HTTPResponse(
            status_code=xhr.status,
            content=xhr.responseText,
        )
    else:  # running natively, so we can use requests. pyodide can't use requests since it uses sockets, which isn't available in the browser
        import requests

        if body_json_str:
            result = getattr(requests, verb.lower())(f"{api_url}{path}", data=body_json_str)
        else:
            result = getattr(requests, verb.lower())(f"{api_url}{path}")
        result.raise_for_status()  # so 4xx and 5xx responses throw an error
        return HTTPResponse(
            status_code=result.status_code,
            content=result.text,
        )


def get_variable_name_current_function_return_is_assigned_to(stack: List[inspect.FrameInfo]) -> Tuple[str, Positions]:
    """Extracts variable name (which serves as a part reference designator) from stack trace part declaration."""
    
    for i, frame in enumerate(stack):
        if frame.function != inspect.currentframe().f_back.f_code.co_name:
            continue
        called_from_frame = stack[i + 1]  # This function Part() was called _from_ this frame
        code = called_from_frame.code_context
        if len(code) != 1:
            raise UserFeedback(f'For some reason the code list has multiple elements: {code}')
        code = code[0]
        lhs = code.split('=')[0].strip()  # Left hand side of the equals sign
        if lhs.isidentifier():  # If assigning to a regular variable
            ref = lhs
            break  # done finding ref
        elif lhs.count('[') == 1 and lhs.count(']') == 1:  # Something like 'R[3+i]'
            base_char = lhs.split('[')[0]
            index = lhs.split('[')[1].split(']')[0]
            leftover = lhs.split('[')[1].split(']')[1]
            if leftover != '':
                raise UserFeedback(
                    f'There is content to the right of [ ]. That is not supported yet.'
                    f'The content to the left of ] is currently: {leftover}'
                )

            # Convert things like 'R[3+i]' to 'R[5]' for i=2
            evaled_index = eval(index, None, called_from_frame.frame.f_locals)
            evaled_index = repr(evaled_index)  # So strings are quoted, tuples are in (), etc.
            ref = f'{base_char}[{evaled_index}]'
            break  # done finding ref
        else:
            raise UserFeedback(
                f'We currently only support assigning self.Part() to simple variable names, '
                f'or to a variable with a single subscript like R[i+3].'
                f'You are currently trying to assign it to: {lhs}'
            )
    else:
        raise UserFeedback('Could not extract the variable name to know the ref')

    return ref, called_from_frame.positions


def convert_cst_to_str(arg):
    """
    Convert a parsed cst (concrete syntax tree) object from libcst to a string
    """
    return cst.Module(body=[cst.SimpleStatementLine([cst.Expr(value=arg)])]).code.strip()


def format_with_si(value):
    if value == 0:
        return '0'
    abs_val = abs(value)
    sign = '-' if value < 0 else ''
    log_val = math.log10(abs_val)
    exp = int(math.floor(log_val / 3.0) * 3)
    prefix_dict = {
        -18: 'a',
        -15: 'f',
        -12: 'p',
        -9: 'n',
        -6: 'µ',
        -3: 'm',
        0: '',
        3: 'k',
        6: 'M',
        9: 'G',
        12: 'T',
    }
    prefix = prefix_dict[exp]
    scale = 10 ** exp
    mant = abs_val / scale
    mant_str = '{:g}'.format(mant)
    return sign + mant_str + prefix


e_series_from_tolerance = {
    40: 'E3',
    20: 'E6',
    10: 'E12',
    5: 'E24',
    2: 'E48',
    1: 'E96',
    .5: 'E192',
}
e_series = {
    'E3': [1.0, 2.2, 4.7],
    'E6': [1.0, 1.5, 2.2, 3.3, 4.7, 6.8],
    'E12': [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2],
    'E24': [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1],
    'E48': [1.00, 1.05, 1.10, 1.15, 1.21, 1.27, 1.33, 1.40, 1.47, 1.54, 1.62, 1.69, 1.78, 1.87, 1.96, 2.05, 2.15, 2.26, 2.37, 2.49, 2.61, 2.74, 2.87, 3.01, 3.16, 3.32, 3.48, 3.65, 3.83, 4.02, 4.22, 4.42, 4.64, 4.87, 5.11, 5.36, 5.62, 5.90, 6.19, 6.49, 6.81, 7.15, 7.50, 7.87, 8.25, 8.66, 9.09, 9.53],
    'E96': [1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27, 1.30, 1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58, 1.62, 1.65, 1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15, 2.21, 2.26, 2.32, 2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09, 3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12, 4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23, 5.36, 5.49, 5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65, 6.81, 6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06, 8.25, 8.45, 8.66, 8.87, 9.09, 9.31, 9.53, 9.76],
    'E192': [1.00, 1.01, 1.02, 1.04, 1.05, 1.06, 1.07, 1.09, 1.10, 1.11, 1.13, 1.14, 1.15, 1.17, 1.18, 1.20, 1.21, 1.23, 1.24, 1.26, 1.27, 1.29, 1.30, 1.32, 1.33, 1.35, 1.37, 1.38, 1.40, 1.42, 1.43, 1.45, 1.47, 1.49, 1.50, 1.52, 1.54, 1.56, 1.58, 1.60, 1.62, 1.64, 1.65, 1.67, 1.69, 1.72, 1.74, 1.76, 1.78, 1.80, 1.82, 1.84, 1.87, 1.89, 1.91, 1.93, 1.96, 1.98, 2.00, 2.03, 2.05, 2.08, 2.10, 2.13, 2.15, 2.18, 2.21, 2.23, 2.26, 2.29, 2.32, 2.34, 2.37, 2.40, 2.43, 2.46, 2.49, 2.52, 2.55, 2.58, 2.61, 2.64, 2.67, 2.71, 2.74, 2.77, 2.80, 2.84, 2.87, 2.91, 2.94, 2.98, 3.01, 3.05, 3.09, 3.12, 3.16, 3.20, 3.24, 3.28, 3.32, 3.36, 3.40, 3.44, 3.48, 3.52, 3.57, 3.61, 3.65, 3.70, 3.74, 3.79, 3.83, 3.88, 3.92, 3.97, 4.02, 4.07, 4.12, 4.17, 4.22, 4.27, 4.32, 4.37, 4.42, 4.48, 4.53, 4.59, 4.64, 4.70, 4.75, 4.81, 4.87, 4.93, 4.99, 5.05, 5.11, 5.17, 5.23, 5.30, 5.36, 5.42, 5.49, 5.56, 5.62, 5.69, 5.76, 5.83, 5.90, 5.97, 6.04, 6.12, 6.19, 6.26, 6.34, 6.42, 6.49, 6.57, 6.65, 6.73, 6.81, 6.90, 6.98, 7.06, 7.15, 7.23, 7.32, 7.41, 7.50, 7.59, 7.68, 7.77, 7.87, 7.96, 8.06, 8.16, 8.25, 8.35, 8.45, 8.56, 8.66, 8.76, 8.87, 8.98, 9.09, 9.20, 9.31, 9.42, 9.53, 9.65, 9.76, 9.88]
}


def closest_value(value, tolerance='20%'):
    """ This function takes a number and converts it to values that suppliers actually carry
    (based on the tolerance provided) """
    if value == 0:
        return '0'
    tolerance = tolerance.strip('%')
    tolerance = float(tolerance)
    series = e_series_from_tolerance[tolerance]
    mantissas = e_series.get(series)
    logv = math.log10(abs(value))  # ok to do abs() here, because
    exp = math.floor(logv)
    candidates = []
    for de in [-1, 0, 1]:
        for m in mantissas:
            sign = 1 if value > 0 else -1
            candidates.append(sign * m * 10 ** (exp + de))
    closest = min(candidates, key=lambda c: abs(c - value))
    return format_with_si(closest)
