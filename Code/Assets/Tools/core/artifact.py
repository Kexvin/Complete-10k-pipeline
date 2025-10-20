from dataclasses import dataclass, asdict, fields
from typing import Any, Dict, Type, TypeVar

T = TypeVar("T", bound="Artifact")

@dataclass
class Artifact:
    schema_version: str = "1.0"
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        fset = {f.name for f in fields(cls)}
        missing = [n for n in fset if n not in data]
        if missing:
            raise ValueError(f"Missing fields for {cls.__name__}: {missing}")
        return cls(**{k: data[k] for k in fset})  # type: ignore[arg-type]