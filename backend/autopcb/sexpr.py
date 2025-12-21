import re
import sys
from dataclasses import fields, is_dataclass, dataclass, MISSING
from typing import List, Optional, Union, Tuple, get_origin, get_args, get_type_hints

from autopcb.parsers.kicad.sexpr import parse_sexp

POSITIONAL_FIELD_METADATA_FLAG = 'positional_flag'
BOOLEAN_FLAG_ATTRIBUTE_METADATA_FLAG = 'flag_attribute'


dbg = False

term_regex = r'''(?mx)
    \s*(?:
        (?P<brackl>\()|
        (?P<brackr>\))|
        (?P<num>[+-]?\d+\.\d+(?=[\ \)])|\-?\d+(?=[\ \)]))|
        (?P<sq>"(?:[^"]|(?<=\\)")*"(?:(?=\))|(?=\s)))|
        (?P<s>[^(^)\s]+)
       )'''

def parse_sexp(sexp):
    stack = []
    out = []
    if dbg: print("%-6s %-14s %-44s %-s" % tuple("term value out stack".split()))
    for termtypes in re.finditer(term_regex, sexp):
        term, value = [(t,v) for t,v in termtypes.groupdict().items() if v][0]
        if dbg: print("%-7s %-14s %-44r %-r" % (term, value, out, stack))
        if   term == 'brackl':
            stack.append(out)
            out = []
        elif term == 'brackr':
            assert stack, "Trouble with nesting of brackets"
            tmpout, out = out, stack.pop(-1)
            out.append(tmpout)
        elif term == 'num':
            v = float(value)
            if v.is_integer(): v = int(v)
            out.append(v)
        elif term == 'sq':
            out.append(value[1:-1].replace(r'\"', '"'))
        elif term == 's':
            out.append(value)
        else:
            raise NotImplementedError("Error: %r" % (term, value))
    assert not stack, "Trouble with nesting of brackets"
    return out[0]

def parse_primitive(t_original, lst):
    t = get_type_sanitized(t_original)

    if t is Union:
        args = get_args(t)
        # Try each type
        for sub_t in args:
            if sub_t is type(None):
                continue
            return parse_primitive(sub_t, lst)

    if t is list:
        args = get_args(t_original)
        item_t = args[0]
        values = []
        for item in lst:
            values.append(
                parse_primitive(item_t, [item]) if not is_dataclass(item_t) else parse_dataclass(item_t, item))
        return values

    if t is tuple:
        args = get_args(t)
        values = []
        for i, sub_t in enumerate(args):
            if i >= len(lst):
                values.append(None)
            else:
                values.append(parse_primitive(sub_t, [lst[i]]))
        return tuple(values)

    if t is dict:
        args = get_args(t)
        # Assume Dict[str, Any] or specific
        d = {}
        i = 0
        while i < len(lst):
            key = lst[i]
            i += 1
            val = lst[i]
            i += 1
            d[key] = val
        return d

    if t == float:
        return float(lst[0])

    if t == int:
        return int(lst[0])

    if t == str:
        return str(lst[0])

    if t == bool:
        if len(lst) == 0:
            # some bools are true if the arg is present
            # (such as `(filled_polygon (layer "F.Cu") island ...)`
            # which means island is True)
            return True
        v = lst[0]
        if v == "yes" or v == "true":
            return True
        if v == "no" or v == "false":
            return False
        return bool(v)

    if t == Tuple[Optional[bool], Optional[bool]]:

        front = None
        back = None
        if all(isinstance(l, str) for l in lst):
            front = False
            back = False
            for l in lst:
                if l == "front":
                    front = True
                elif l == "back":
                    back = True
                elif l == "none":
                    front = None
                    back = None
        else:
            for item in lst:
                if item[0] == "front":
                    v = item[1]
                    front = v == "yes" if v != "none" else None
                elif item[0] == "back":
                    v = item[1]
                    back = v == "yes" if v != "none" else None
        return (front, back)

    # For other tuples, positional
    if get_type_sanitized(t) == tuple:
        return tuple(parse_primitive(sub_t, [lst[i]]) for i, sub_t in enumerate(args))

    raise ValueError("Unknown primitive type " + str(t) + " for " + str(lst))


def get_type_sanitized(t):
    """Convert Optional[Type] to Type, and remove subscripts like List[int] -> int"""
    type_without_subscript = get_origin(t)
    if type_without_subscript == Union or type_without_subscript == Optional:
        args = get_args(t)
        if len(args) != 2 and None not in args:
            raise Exception(f"The only union type supported is Something | None. We haven't added support "
                            f"for other unions yet. The current type annotation is {args}")
        # get the type that is not NoneType
        return next(a for a in args if a is not type(None))
    elif type_without_subscript is not None:
        return type_without_subscript
    else:
        return t  # the type didn't have a subscript, so get_origin returns None so use regular type() function


def remove_optional_type_wrapper(t):
    """Convert Optional[Type] to Type. Doesn't do anything if not Optional[] or | None for type annotated"""
    type_without_subscript = get_origin(t)
    if type_without_subscript == Union or type_without_subscript == Optional:
        args = get_args(t)
        if len(args) != 2 and None not in args:
            raise Exception(f"The only union type supported is Something | None. We haven't added support "
                            f"for other unions yet. The current type annotation is {args}")
        # get the type that is not NoneType
        return next(a for a in args if a is not type(None))
    else:
        return t  # the type didn't have a subscript, so get_origin returns None so use regular type() function


def is_optional(type_hint) -> bool:
    """
    Returns True if the type hint is Optional[something], False otherwise.
    """
    # Optional[T] resolves to Union[T, None]
    origin = get_origin(type_hint)
    if origin is Union:
        args = get_args(type_hint)
        # Check if exactly two args: one is NoneType, the other is anything else
        if len(args) == 2 and type(None) in args:
            return True
    return False


def is_list_type(t) -> bool:
    """Check if t is list[something], e.g., list[str] or List[int]."""
    origin = get_origin(t)
    if origin is None:
        return issubclass(t, list)
    return origin is list or origin is List  # Handles both built-in list and typing.List


def is_optional_list_type(t) -> bool:
    """Check if t is Optional[list[something]], e.g., Optional[list[str]]."""
    origin = get_origin(t)
    if origin is not Union and origin is not Optional:  # Optional is syntactic sugar for Union[..., None]
        return False
    args = get_args(t)
    # Ensure None is one arg, and exactly one other arg is a list type
    non_none_args = [arg for arg in args if arg is not type(None)]
    return (
            type(None) in args
            and len(non_none_args) == 1
            and is_list_type(non_none_args[0])
    )


def is_list_or_optional_list(t) -> bool:
    """Combined check: True if t is list[something] or Optional[list[something]]."""
    return is_list_type(t) or is_optional_list_type(t)


def convert_plural_to_singular_if_list(name, variable_type):
    """If type is a list, then convert the name to singular, like vias -> via"""
    if get_type_sanitized(variable_type) != list:
        return name
    # typing.List[__main__.LayerList] doesn't follow the pattern
    if name == 'layers':  # and typing.get_origin(variable_type) is list and typing.get_args(variable_type) == (LayerList,):
        return name
    if name[-3:] == 'ies':
        return name[:-3] + 'y'
    if name[-3:] == 'xes':  # for boxes -> box
        return name[:-3] + 'x'
    return name[:-1]  # remove the trailing 's'


@dataclass
class ParsingStackElement:
    attribute_name: str
    # attribute_index is if there is multiple of the same attribute (so it's a list, like many footprint in a pcb)
    attribute_index: Optional[int] = None
# Used to keep track of what we are parsing when going recursively
# Technically not needed, but useful for debugging
parsing_stack: list[ParsingStackElement] = []


def parse_dataclass(cls,
                    sexp,
                    attribute_name: str,
                    attribute_index: Optional[int] = None,
                    print_debug=False):
    parsing_stack.append(ParsingStackElement(attribute_name, attribute_index))

    # if not f.name.startswith('_') to filter out private attributes
    fields_dict = {convert_plural_to_singular_if_list(f.name, f.type): f for f in fields(cls) if not f.name.startswith('_')}
    fields_list = list(fields_dict.values())

    attribute_values = {}

    how_many_boolean_flags_parsed = 0
    _preserve_interleaved_order_values: list[str] = []

    for row, item in enumerate(sexp):
        if row == 0 and not hasattr(cls, '_index_from_0'):
            # skip the 0th item, as it is the type name. Ex. (layer "B.Cu" (type "copper"))
            # except for classes (like Layer) that don't have the class name as the 0th element:
            # Ex. (4 "In4.Cu" power "Ground2")
            continue
        dataclass_field = None  # reset from previous loop iteration
        try:
            if isinstance(item, list):  # If the sexpression is of the form (attr_name stuff stuff stuff)
                key = item[0]
                from autopcb.datatypes.pcb import LayerList
                if cls.__name__ == LayerList.__name__:  # compare names rather than the actual objects, since the import paths could be different (ex. if debugging the pcb.py locally, cls will be __main__.LayerList while the right hand side will be autopcb.dataclasses.pcb.LayerList
                    # There is one class (Layer) in the entire file format
                    # that doesn't include the key type as the 0th element,
                    # so we have to manually specify its type
                    # Ex. (4 "In4.Cu" power "Ground2")
                    key = 'layer_info'
                if print_debug:
                    print('Parsing:',
                          '.'.join([attr.attribute_name + (f'[{attr.attribute_index}]' if attr.attribute_index is not None else '') for attr in parsing_stack])+'.'+key)

                if key in fields_dict:
                    dataclass_field = fields_dict[key]
                    t = dataclass_field.type

                    if is_list_or_optional_list(t):  # todo fixme: why did I previously have `and len(item[1:])>1:`
                        item_t = get_args(dataclass_field.type)[0]
                        if is_dataclass(item_t):
                            val = attribute_values.get(dataclass_field.name, [])
                            add_to_value = parse_dataclass(item_t, item, key, len(val), print_debug=print_debug)
                            val.append(add_to_value)
                        else:
                            val = [parse_primitive(item_t, [element]) for element in item[1:]]

                        if key in [convert_plural_to_singular_if_list(i, list) for i in getattr(cls, '_preserve_interleaved_order', [])]:
                            # _preserve_interleaved_order is a list of strings, of attribute names,
                            # that should have their interleaved ordering preserved when serializing again
                            setattr(val[-1], '_order_index', row)
                    else:
                        t_concrete = remove_optional_type_wrapper(t)
                        val = parse_dataclass(t_concrete, item, key, print_debug=print_debug) if is_dataclass(t_concrete) else parse_primitive(t_concrete, item[1:])
                        # arg of convert_plural_to_singular_if_list anything other than list
                        if key in [convert_plural_to_singular_if_list(i, int) for i in getattr(cls, '_preserve_interleaved_order', [])]:
                            # _preserve_interleaved_order is a list of strings, of attribute names,
                            # that should have their interleaved ordering preserved when serializing again
                            setattr(val, '_order_index', row)
                    attribute_values[dataclass_field.name] = val
                    continue

                print('Parsing:',
                      '.'.join([attr.attribute_name + (f'[{attr.attribute_index}]' if attr.attribute_index is not None else '') for attr in parsing_stack])+'.'+key,
                      file=sys.stderr)
                print('\033[91mWARNING: Unrecognized attribute (dropping from data):', item, '\033[0m', file=sys.stderr)
            else:
                # Parsing a scalar (Positional attribute, or boolean flag attribute)
                # Ex. Positional `smd` in (footprint smd (at 0 0))
                # Ex. Boolean flag `unlocked` in (footprint (at 0 0) unlocked)

                type_annotations = get_type_hints(cls)
                # todo fixme
                # how should we handle the case of a positional arg's value matching the name of a boolean arg?
                # that will fail paring right now

                # boolean arg, where the presence of the key means the attribute is true
                if item in fields_dict and fields_dict[item].metadata.get(BOOLEAN_FLAG_ATTRIBUTE_METADATA_FLAG, False):
                    how_many_boolean_flags_parsed += 1
                    t = bool
                    attr_name = item
                    if print_debug:
                        print('Parsing:',
                              '.'.join([attr.attribute_name + (f'[{attr.attribute_index}]' if attr.attribute_index is not None else '') for attr in parsing_stack])+'.'+attr_name)
                else:  # positional arg
                    # we need how_many_boolean_flags_parsed for parsing things like, where oval is a boolean flag,
                    # and 1 and 2 are positional args for x and y
                    # (drill 1 2)
                    # (drill oval 1 2)
                    dataclass_field = fields_list[row - (1 if not hasattr(cls, '_index_from_0') else 0) - how_many_boolean_flags_parsed]
                    t = dataclass_field.type
                    attr_name = dataclass_field.name
                    if print_debug:
                        print('Parsing:',
                              '.'.join([attr.attribute_name + (f'[{attr.attribute_index}]' if attr.attribute_index is not None else '') for attr in parsing_stack])+'.'+attr_name)
                    if (POSITIONAL_FIELD_METADATA_FLAG not in dataclass_field.metadata
                            or dataclass_field.metadata[POSITIONAL_FIELD_METADATA_FLAG] == False):
                        print()
                        print(f'Currently parsing this data for the dataclass `{cls.__name__}`')
                        print(sexp)
                        print()
                        print(f'Error parsing index {row} that has value `{item}`. '
                              f'Could not figure out what attribute it belongs to. It doesn\'t match '
                              f'"{dataclass_field.name}"')
                        print()
                        print(f"Hint: The value `{item}` is a scalar (ex. the attribute "
                              f"with the value smd is of the form "
                              f"(footprint smd) rather than (footprint (package smd), "
                              f"so it has to be a positional argument. But the next available argument "
                              f"`\033[91m{dataclass_field.name}\033[0m` is not marked to allow positional arguments. "
                              f"If you want to mark that attribute as positional, add "
                              f"`= positional()` to the right hand side of the attribute.")
                        raise ValueError(f"Error parsing {cls.__name__}: Could not parse positional argument at index {row} with value `{item}`. The attribute `{dataclass_field.name}` is not marked to allow positional arguments.")

                # todo fixme: raise error if the item type doesn't match t the dataclass type
                val = parse_primitive(t, [item])
                attribute_values[attr_name] = val

        except () as e:  # should we bring this back? except TypeError, IndexError, ValueError
            print(e)
            print(f'Error parsing {cls.__name__}. Here is what the parser thinks:\n'
                  f'Currently attribute number {row} of the data for {cls.__name__} is being parsed.\n'
                  f'The data for the attribute number {row} being parsed = {item}.\n'
                  f'The parser thinks that this data is '
                  f'{"another class" if isinstance(item, list) else "a positional or boolean attribute"}')
            if dataclass_field is None:
                print(f'The parser was not able to figure out which attribute of {cls.__name__} the data is for')
            else:
                print(f'The parser think the data above is for {cls.__name__}.{dataclass_field.name}')
            print('You probably want to start the debugger here so you can figure out what\'s wrong (either your '
                  'data shape (dataclasses) is wrong for the file format, or there\'s a bug in the parser, '
                  'which is also likely)')
            quit()
            # breakpoint()
        row += 1  # this is the end of the loop, increment the counter

    # Fill in default values for non-optional attributes,
    # so the data is guaranteed to match the shape (for safety in typescript)
    fields_dict = {f.name: f for f in fields(cls)}
    for attribute_name, type_hint in get_type_hints(cls).items():
        if attribute_name.startswith('_'):
            continue  # skip private attributes
        if attribute_name not in attribute_values:  # if the attribute was not found in the data
            # Check if the field has a default or default_factory defined
            field_obj = fields_dict.get(attribute_name)
            if field_obj.default is not MISSING or field_obj.default_factory is not MISSING:
                # Skip - let the dataclass handle the default value
                continue

            if is_optional(type_hint):
                attribute_values[attribute_name] = None
            else:
                attribute_type = get_type_sanitized(type_hint)
                # todo fixme implement this later
                # print(f'\033[91mWARNING: attribute {attribute_name} is required (type {type_hint} is not Optional[]), '
                #       f'but is missing for file. Auto filling default value to guarantee data shape and type.\033[0m')
                if issubclass(attribute_type, bool):  # must be before checking if subclass of int, because bool is a subclass of int in python
                    attribute_values[attribute_name] = False
                elif issubclass(attribute_type, float):
                    attribute_values[attribute_name] = 0.0
                elif issubclass(attribute_type, int):
                    attribute_values[attribute_name] = 0
                elif issubclass(attribute_type, str):
                    attribute_values[attribute_name] = ''
                elif issubclass(attribute_type, list):
                    attribute_values[attribute_name] = []
                elif issubclass(attribute_type, dict):
                    attribute_values[attribute_name] = {}
                else:
                    print(f'\033[91mAttribute .{attribute_name} with type {attribute_type.__name__} in class {cls.__name__} is marked as required, '
                          f'but isn\'t in the file being parsed\033[0m')
                    raise NotImplementedError()
    parsing_stack.pop()
    return cls(**attribute_values)


# Serializer

def serialize_primitive(val):
    t = type(val)

    if val is None:
        return []

    if t == float or t == int:
        return [val]

    if t == str:
        return [val]

    if t == bool:
        return ["yes" if val else "no"]

    # if t == Vector2:
    #     return [val.x, val.y]  # Without "xy" for most, but for pts with
    #
    # if t == Vector3:
    #     return ["xyz", val.x, val.y, val.z]

    # todo fixme I think we can remove this (I think it's not used anymore)
    # if t == ShapeLineChain:
    #     ser = ["pts"]
    #     for p in val.points:
    #         if isinstance(p, Vector2):
    #             ser.append(["xy", p.x, p.y])
    #         elif isinstance(p, Arc):
    #             ser.append(
    #                 ["arc", ["start", p.start.x, p.start.y], ["mid", p.mid.x, p.mid.y], ["end", p.end.x, p.end.y]])
    #     return ser

    # if t == Arc:
    #     return ["arc", ["start", val.start.x, val.start.y], ["mid", val.mid.x, val.mid.y],
    #             ["end", val.end.x, val.end.y]]

    if get_type_sanitized(t) == tuple:
        ser = []
        args = get_args(t)
        for v, sub_t in zip(val, args):
            if v is not None:
                sub_ser = serialize_primitive(v)
                if sub_t == bool:
                    ser.append(["front" if len(ser) == 0 else "back", "yes" if v else "no"])
                else:
                    ser.extend(sub_ser)
        return ser

    if get_type_sanitized(t) == list:
        ser = []
        for v in val:
            ser.extend(serialize_primitive(v))
        return ser

    raise ValueError("Unknown serialize primitive " + str(t))


def serialize_dataclass(instance):
    from autopcb.datatypes.schematics import SchPageInfo as PageInfo
    cls = type(instance)
    sexp = []

    # Collect flags and positionals separately for the header (scalars)
    flags = []
    positionals = []

    for f in fields(cls):
        if f.name.startswith('_'):
            continue  # skip private fields
        val = getattr(instance, f.name)
        if val is None:
            continue

        if f.metadata.get(BOOLEAN_FLAG_ATTRIBUTE_METADATA_FLAG, False):
            if val:
                flags.append(f.name)
        elif f.metadata.get(POSITIONAL_FIELD_METADATA_FLAG, False):
            ser = serialize_primitive(val)
            positionals.extend(ser)

        # Special handling integrated into the loop where possible
        if cls == PageInfo and f.name == "type":
            if val == "Custom" and instance.width is not None and instance.height is not None:
                positionals.append(instance.width)
                positionals.append(instance.height)

    # Add positionals first, then flags
    sexp.extend(positionals)
    sexp.extend(flags)

    # tuple is (order_index, the s expression element)
    order_preserved_attributes: list[tuple[int, list | str | int | float]] = []
    index_to_add_ordered_attributes_to = None

    # Now handle regular keyed fields (non-positional, non-flag)
    for f in fields(cls):
        if f.name.startswith('_'):
            continue  # skip private fields

        if f.name in getattr(cls, '_preserve_interleaved_order', []) and index_to_add_ordered_attributes_to is None:
            index_to_add_ordered_attributes_to = len(sexp)

        if f.metadata.get(POSITIONAL_FIELD_METADATA_FLAG, False) or f.metadata.get(BOOLEAN_FLAG_ATTRIBUTE_METADATA_FLAG, False):
            continue

        val = getattr(instance, f.name)
        if val is None:
            continue

        # Special cases
        from autopcb.datatypes.schematics import SchTitleBlock as TitleBlock
        if cls == TitleBlock and f.name == "comments":
            for idx, c in enumerate(val):
                sexp.append(["comment", idx + 1, c])
            continue

        if cls == PageInfo and f.name == "portrait":
            if val:
                sexp.append("portrait")
            continue

        if cls == PageInfo and f.name in ("width", "height"):
            # Skip if already handled positionally in 'type' special case
            continue

        # Determine the key to use in S-expression
        key = convert_plural_to_singular_if_list(f.name, f.type) if is_list_or_optional_list(f.type) else f.name

        t = f.type
        if is_list_or_optional_list(t):
            if is_dataclass(get_type_sanitized(get_args(t)[0])):
                for item in val:
                    item_ser = serialize_dataclass(item)
                    if hasattr(item, '_index_from_0') and item._index_from_0:
                        # for example, for the net data here:
                        # (kicad_pcb
                        #   (layers
                        #     (0 "F.Cu" signal "Top")
                        #     (4 "In1.Cu" power "Ground")
                        #     (6 "In2.Cu" signal "Inner")
                        item_to_add = item_ser
                    else:
                        item_to_add = [key] + item_ser

                    if f.name in getattr(cls, '_preserve_interleaved_order', []):
                        order_preserved_attributes.append((getattr(item, '_order_index'), item_to_add))
                    else:
                        sexp.append(item_to_add)
            else:
                if len(val) > 0:
                    item_ser = [serialize_primitive(item)[0] for item in val]
                    item_to_add = [key] + item_ser

                    if f.name in getattr(cls, '_preserve_interleaved_order', []):
                        order_preserved_attributes.append((getattr(item, '_order_index'), item_to_add))
                    else:
                        sexp.append(item_to_add)
        elif get_type_sanitized(t) == dict:
            # Flatten dict into key-value pairs (assuming values are primitives unless dataclass)
            flat_ser = []
            for dk, dv in val.items():
                flat_ser.append(dk)
                if is_dataclass(type(dv)):
                    flat_ser.append(serialize_dataclass(dv))
                else:
                    flat_ser.append(dv)  # primitive
            if flat_ser:
                sexp.append([key] + flat_ser)
                # todo do we need to support order_preserved_attributes here?
        else:
            ser = serialize_dataclass(val) if is_dataclass(get_type_sanitized(t)) else serialize_primitive(val)
            sexp.append([key] + ser)
            # todo do we need to support order_preserved_attributes here?

    ordered_attributes_to_add = [i[1] for i in sorted(order_preserved_attributes, key=lambda e: e[0])]
    if index_to_add_ordered_attributes_to is None:
        sexp.extend(ordered_attributes_to_add)  # add it to the end if no attribute before marked to splice it earlier
    else:
        sexp = sexp[:index_to_add_ordered_attributes_to] + ordered_attributes_to_add + sexp[index_to_add_ordered_attributes_to:]

    return sexp


def to_sexp(sexp, indentation_level=1, quote_str=True):
    if not isinstance(sexp, list):  # if it's a scalar primitive
        if isinstance(sexp, str):
            if not quote_str or sexp in ['yes', 'no', 'thru_hole', 'smd', 'connect', 'np_thru_hole',
                                         'circle', 'rectangle', 'rect', 'roundrect', 'oval', 'trapezoid', 'custom',
                                         'signal', 'power', 'user',
                                         'locked', 'full',
                                         'front', 'back',
                                         'solid', 'dash', 'dash_dot', 'dash_dot_dot', 'dot', 'default',
                                         'edge',
                                         'padvia', 'value', 'reference', 'user',
                                         'board_only', 'exclude_from_pos_files', 'exclude_from_bom',
                                         'through_hole',
                                         'left', 'right', 'top', 'bottom',
                                         'knockout',
                                         'aligned',  # for (dimension
                                         'outward',
                                         'none', 'outline', 'color', 'background',  # for fill value
                                         'input', 'output', 'bidirectional', 'tri_state', 'passive', 'unspecified', 'power_in', 'power_out', 'open_collector', 'open_emitter', 'free', 'no_connect',  # for pin type
                                         'line', 'inverted', 'clock', 'inverted_clock', 'input_low', 'clock_low', 'output_low', 'edge_clock_high', 'non_logic',  # for pin style
                                         'x', 'y',  # for mirror
                                         'hide', 'italic', 'bold',
                                         'other',  # for embedded file . type
                                         'allowed', 'not_allowed',
                                         'mirror',
                                         'blind', 'buried', 'micro'  # via type flags
                                         ]:
                return sexp
            else:
                # todo fixme make sure we have fully correct escaping
                # s = sexp.replace('\\', '\\\\').replace('"', '\\"')
                s = sexp.replace('"', '\\"')
                return f'"{s}"'
        elif isinstance(sexp, float):
            if sexp.is_integer():
                return str(int(sexp))  # to match the formatting kicad uses, don't include decimals if not needed
            else:
                return f'{sexp:f}'.rstrip('0').rstrip('.')  # use this to convert to string, since str(a float) uses e notation if small
        else:
            return str(sexp)

    parts = []

    parts.append("(")

    multiline = False
    first_loop = True
    attributes_whos_values_arent_quoted = ['data', 'layerselection', 'plot_on_all_layers_selection']
    is_embedded_file_data_attribute = len(sexp) >= 2 and sexp[0] in attributes_whos_values_arent_quoted
    for i, s in enumerate(sexp):
        if isinstance(s, list):
            # ---- BEGIN: (xy …) special-case handling (keep on current line until col 99) ----
            if len(s) > 0 and isinstance(s[0], str) and s[0] == 'xy':
                token = to_sexp(s, indentation_level=indentation_level+1)
                current_line_len = len("".join(parts).split("\n")[-1])
                # add one space before token when staying on same line
                if current_line_len + 1 + len(token) <= 99:
                    parts.append(' ')
                    parts.append(token)
                else:
                    if parts[-1] == ' ':
                        parts.pop()
                    parts.append('\n' + '\t' * indentation_level + token)
                    multiline = True
            else:
                # ---- END: (xy …) special-case handling ----
                if parts[-1] == ' ':
                    parts.pop()  # remove last space since it's not needed since we're going to add a newline
                parts.append('\n'+'\t'*indentation_level+to_sexp(s, indentation_level=indentation_level+1))
                multiline = True
        else:  # if it's a scalar primitive
            if is_embedded_file_data_attribute and s not in attributes_whos_values_arent_quoted:  # no special case handling for the 0th element since it's the key (doesn't need special case to be unquoted)
                # for some reason kicad doesn't quote the data attribute of embedded files (I think it's base64)
                parts.append('\t'*indentation_level if i >= 2 else '')  # only need indentation starting after the newline, after (data the_first_part_of_data \n now indent
                parts.append(s)
                if len(sexp) > 2:  # (data stuff_in_data\n fall on first line, so only multiline if more than that
                    parts.append('\n')
                    multiline = True
            else:
                # quote_str=not first_loop to not put the attribute name ex. `(footprint` in quotes like `("footprint"`
                parts.append(to_sexp(s, indentation_level=indentation_level+1, quote_str=not first_loop))
                parts.append(' ')
        first_loop = False

    if parts[-1] == ' ':
        parts.pop()  # remove last space

    parts.append('\n'+'\t'*(indentation_level-1)+')' if multiline else ')')

    return "".join(parts)


if __name__ == '__main__':
    from pathlib import Path

    # update these three lines to change between schematics and pcb
    file_header = 'kicad_sch'
    from autopcb.datatypes.schematics import Schematic as FileType
    f = Path('/home/caspian/Downloads/Complex PCB test for autopcb parser/asd.kicad_sch').read_text()

    sexp_list = parse_sexp(f)
    if sexp_list[0] != file_header:
        raise ValueError("Not a Kicad PCB file")
    board = parse_dataclass(FileType, sexp_list, file_header, print_debug=False)
    new_board = [file_header] + serialize_dataclass(board)
    print(to_sexp(new_board))
