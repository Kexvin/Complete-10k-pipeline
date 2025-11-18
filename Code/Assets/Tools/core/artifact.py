from dataclasses import dataclass, asdict, fields, Field, MISSING
from typing import Any, Dict, Type, TypeVar

T = TypeVar("T", bound="Artifact")


@dataclass
class Artifact:
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create an artifact from a dict, using field defaults for missing values.

        This is tolerant to missing keys so deserialization from older/newer schemas won't fail.
        """
        init_kwargs: Dict[str, Any] = {}
        for f in fields(cls):
            if f.name in data:
                init_kwargs[f.name] = data[f.name]
            else:
                # Use default if available, otherwise use default_factory when present
                if f.default is not MISSING:
                    init_kwargs[f.name] = f.default
                elif getattr(f, 'default_factory', MISSING) is not MISSING:  # type: ignore[attr-defined]
                    try:
                        init_kwargs[f.name] = f.default_factory()  # type: ignore[operator]
                    except Exception:
                        init_kwargs[f.name] = None
                else:
                    init_kwargs[f.name] = None

        return cls(**init_kwargs)  # type: ignore[arg-type]