from dataclasses import fields, is_dataclass
import json
import re
import dacite
from pathlib import Path
from typing_extensions import Self
from autopcb.parsers.kicad.parser import parse_dataclass, parse_sexp, serialize_dataclass, to_sexp


class DataclassSerializerMixin:
    """Mixin class for dataclass parsing and serialization."""

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Instantiates the class from a dict string using dacite, treating uuid.UUID and str as equivalent types."""
        return dacite.from_dict(
            data_class=cls,
            data=data,
        )

    @classmethod
    def from_json(cls, json_string: str) -> Self:
        """
        Instantiates the class from a JSON string using dacite, treating uuid.UUID and str as equivalent types.
        """
        return cls.from_dict(json.loads(json_string))

    def asdict(self):
        """Serialize the class as a dictionary."""
        def serialize(obj):
            if is_dataclass(obj):
                return {
                    f.name: serialize(getattr(obj, f.name))
                    for f in fields(obj)
                    if hasattr(obj, f.name) and f.repr is True
                }
            elif isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, (list, tuple)):
                return [serialize(v) for v in obj]
            elif isinstance(obj, dict):
                return {serialize(k): serialize(v) for k, v in obj.items()}
            else:
                return obj

        return serialize(self)

    def dumps(self):
        """Dumps object into JSON"""
        return json.dumps(self.asdict())


class SexprMixin:
    """Mixin class for converting between S-expressions and dataclasses."""
  
    @classmethod
    def from_file(cls, file_path: str) -> Self:
        sexp_list = parse_sexp(Path(file_path).read_text())
        return cls.from_sexpr(sexp_list)

    @classmethod
    def from_sexpr(cls, sexpr: list) -> Self:
        """Instantiates the class from a S-expression list using dacite."""
        parsed_dataclass = parse_dataclass(cls, sexpr, '', print_debug=False)
        return parsed_dataclass

    @classmethod
    def from_sexpr_string(cls, sexpr_string: str) -> Self:
        return cls.from_sexpr(parse_sexp(sexpr_string))

    def to_sexpr(self, file_header: str) -> str:
        file_content = [file_header] + serialize_dataclass(self)
        return to_sexp(file_content)

