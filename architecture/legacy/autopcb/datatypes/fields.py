from dataclasses import field


def positional(**kw):
    """Used to annotate that a dataclass's attribute's value is determined by its position in the s expression
    Ex. the property name ("Reference") and property value ("U4") here:
    (property "Reference" "U4" (at 0 0 90) (unlocked yes)"""
    return field(metadata={'positional_flag': True}, **kw)


def flag_boolean(**kw):
    """Used to annotate the value of a boolean arg is determined by the *presence* of the name in the s expression
    Ex. (footprint unlocked) rather than (footprint (unlocked yes))"""
    return field(metadata={'flag_attribute': True}, **kw)