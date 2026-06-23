from dataclasses import dataclass

from app.services.extract.base import Extractor

_REGISTRY: dict[str, type[Extractor]] = {}
_INSTANCES: dict[str, Extractor] = {}


@dataclass
class ExtractorInfo:
    name: str
    description: str
    needs_ocr: bool
    languages: list[str]


def register_extractor(cls: type[Extractor]) -> type[Extractor]:
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[name] = cls
    return cls


def available_extractors() -> list[ExtractorInfo]:
    return [
        ExtractorInfo(
            name=cls.name,
            description=cls.description,
            needs_ocr=cls.needs_ocr,
            languages=list(cls.languages),
        )
        for cls in _REGISTRY.values()
    ]


def is_registered(name: str) -> bool:
    return name in _REGISTRY


def get_extractor(name: str) -> Extractor:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown extractor: {name!r}")
    if name not in _INSTANCES:
        _INSTANCES[name] = _REGISTRY[name]()
    return _INSTANCES[name]
