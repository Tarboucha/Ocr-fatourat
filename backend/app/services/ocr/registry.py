from dataclasses import dataclass

from app.services.ocr.base import OcrPipeline

# name -> pipeline class
_REGISTRY: dict[str, type[OcrPipeline]] = {}
# name -> lazily-instantiated singleton (models load on first use, reused after)
_INSTANCES: dict[str, OcrPipeline] = {}


@dataclass
class PipelineInfo:
    name: str
    description: str
    supports_region: bool
    languages: list[str]


def register_pipeline(cls: type[OcrPipeline]) -> type[OcrPipeline]:
    """Class decorator: register a pipeline under its `name`. Self-registers on
    import, so importing the module is enough to make it available everywhere."""
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[name] = cls
    return cls


def available_pipelines() -> list[PipelineInfo]:
    return [
        PipelineInfo(
            name=cls.name,
            description=cls.description,
            supports_region=cls.supports_region,
            languages=list(cls.languages),
        )
        for cls in _REGISTRY.values()
    ]


def is_registered(name: str) -> bool:
    return name in _REGISTRY


def get_pipeline(name: str) -> OcrPipeline:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown OCR pipeline: {name!r}")
    if name not in _INSTANCES:
        _INSTANCES[name] = _REGISTRY[name]()  # may load models
    return _INSTANCES[name]
