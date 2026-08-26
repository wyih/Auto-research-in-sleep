"""Typed domain model for results-pack generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


RowType = Literal["coef", "gof", "spec", "note"]
NarrativeMode = Literal["standard", "transport-only"]


class ResultsDocxError(ValueError):
    """Raised when an input violates the results-pack contract."""


@dataclass(frozen=True)
class SourceFile:
    path: Path
    sha256: str
    bytes: int


@dataclass(frozen=True)
class CoefficientRecord:
    source_row: int
    term: str
    term_label: str
    model_id: str
    model_label: str
    row_type: RowType
    estimate: float | None
    std_error: float | None
    p_value: float | None
    value_text: str
    nobs: int | None
    adj_r_squared: float | None
    dependent_variable: str
    fixed_effects: str
    cluster: str
    controls: str
    panel: str


@dataclass(frozen=True)
class CoefficientTable:
    title: str
    source: SourceFile
    records: tuple[CoefficientRecord, ...]
    primary_term: str | None
    primary_model: str | None
    note: str


@dataclass(frozen=True)
class DescriptiveRecord:
    source_row: int
    variable: str
    variable_label: str
    n: int | None
    mean: float | None
    sd: float | None
    p25: float | None
    p50: float | None
    p75: float | None
    minimum: float | None
    maximum: float | None
    sample: str


@dataclass(frozen=True)
class DescriptiveTable:
    title: str
    source: SourceFile
    records: tuple[DescriptiveRecord, ...]
    note: str


@dataclass(frozen=True)
class FigureInput:
    title: str
    path: Path
    source: SourceFile
    source_data: tuple[SourceFile, ...]
    source_script: SourceFile | None
    alt_text: str
    note: str
    transport_figure: bool


@dataclass(frozen=True)
class DocumentSpec:
    title: str
    subtitle: str
    run_id: str
    as_of_date: str
    coefficient_tables: tuple[CoefficientTable, ...]
    descriptive_tables: tuple[DescriptiveTable, ...]
    figures: tuple[FigureInput, ...]
    coefficient_decimals: int
    descriptive_decimals: int
    narrative_mode: NarrativeMode


@dataclass(frozen=True)
class BuildRequest:
    spec_path: Path
    output_path: Path
    author: str
    manifest_path: Path | None = None
    receipt_path: Path | None = None
    force: bool = False


@dataclass(frozen=True)
class NarrativeClaim:
    text: str
    source_path: Path
    source_row: int
    selectors: dict[str, str]
    values: dict[str, str | int | float | None]


@dataclass(frozen=True)
class BuildResult:
    output_path: Path
    manifest_path: Path
    receipt_path: Path
    output_sha256: str
    output_bytes: int
    table_count: int
    figure_count: int
    narrative_claim_count: int
    narrative_mode: NarrativeMode
    metadata_audit: dict[str, object]
