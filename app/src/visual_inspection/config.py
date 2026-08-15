from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    key: str
    label: str
    model_id: str
    base_url: str
    optional: bool = False


MODELS = {
    "reason2-8b": ModelConfig(
        key="reason2-8b",
        label="Cosmos Reason2 8B",
        model_id="nvidia/cosmos-reason2-8b",
        base_url=os.getenv("NIM_8B_BASE_URL", "http://127.0.0.1:8002/v1"),
    ),
    "reason2-2b": ModelConfig(
        key="reason2-2b",
        label="Cosmos Reason2 2B",
        model_id="nvidia/cosmos-reason2-2b",
        base_url=os.getenv("NIM_2B_BASE_URL", "http://127.0.0.1:8001/v1"),
    ),
    "cosmos3-nano": ModelConfig(
        key="cosmos3-nano",
        label="Cosmos3 Nano (optional)",
        model_id="nvidia/cosmos3-nano-reasoner",
        base_url=os.getenv("NIM_NANO_BASE_URL", "http://127.0.0.1:8003/v1"),
        optional=True,
    ),
}

DEFAULT_MODEL = os.getenv("VISUAL_INSPECTION_DEFAULT_MODEL", "reason2-8b")


def model_labels() -> list[str]:
    return [model.label for model in MODELS.values()]


def model_from_label(label: str) -> ModelConfig:
    for model in MODELS.values():
        if model.label == label:
            return model
    raise ValueError(f"Unknown model: {label}")


def default_model_label() -> str:
    return MODELS.get(DEFAULT_MODEL, MODELS["reason2-8b"]).label
