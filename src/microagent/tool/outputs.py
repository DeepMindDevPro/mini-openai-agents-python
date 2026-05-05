"""Structured tool outputs: text / image / file.

Each output has both a Pydantic model (for runtime validation) and a TypedDict variant
(for lightweight authoring in user code). The `ValidToolOutput` union is used by the RunItem
serializer.
"""
from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, model_validator
from typing_extensions import NotRequired, TypedDict


class ToolOutputText(BaseModel):
    """Text payload for the model."""

    type: Literal["text"] = "text"
    text: str


class ToolOutputTextDict(TypedDict, total=False):
    type: Literal["text"]
    text: str


class ToolOutputImage(BaseModel):
    """Image payload. At least one of `image_url` / `file_id` is required."""

    type: Literal["image"] = "image"
    image_url: str | None = None
    file_id: str | None = None
    detail: Literal["low", "high", "auto"] | None = None

    @model_validator(mode="after")
    def _check_at_least_one(self) -> ToolOutputImage:
        if self.image_url is None and self.file_id is None:
            raise ValueError("ToolOutputImage requires image_url or file_id")
        return self


class ToolOutputImageDict(TypedDict, total=False):
    type: Literal["image"]
    image_url: NotRequired[str]
    file_id: NotRequired[str]
    detail: NotRequired[Literal["low", "high", "auto"]]


class ToolOutputFileContent(BaseModel):
    """File payload. At least one of `file_data / file_url / file_id` is required."""

    type: Literal["file"] = "file"
    file_data: str | None = None
    file_url: str | None = None
    file_id: str | None = None
    filename: str | None = None

    @model_validator(mode="after")
    def _check_at_least_one(self) -> ToolOutputFileContent:
        if self.file_data is None and self.file_url is None and self.file_id is None:
            raise ValueError("ToolOutputFileContent requires file_data / file_url / file_id")
        return self


class ToolOutputFileContentDict(TypedDict, total=False):
    type: Literal["file"]
    file_data: NotRequired[str]
    file_url: NotRequired[str]
    file_id: NotRequired[str]
    filename: NotRequired[str]


ValidToolOutput = Union[ToolOutputText, ToolOutputImage, ToolOutputFileContent]
ValidToolOutputDict = Union[ToolOutputTextDict, ToolOutputImageDict, ToolOutputFileContentDict]


__all__ = [
    "ToolOutputFileContent",
    "ToolOutputFileContentDict",
    "ToolOutputImage",
    "ToolOutputImageDict",
    "ToolOutputText",
    "ToolOutputTextDict",
    "ValidToolOutput",
    "ValidToolOutputDict",
]