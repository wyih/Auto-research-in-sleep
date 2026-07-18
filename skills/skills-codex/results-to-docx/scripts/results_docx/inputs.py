"""Load and validate auditable tidy inputs from one JSON build specification."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from collections.abc import Iterable
from typing import Any, Mapping, Sequence, cast

from .model import (
    CoefficientRecord,
    CoefficientTable,
    DescriptiveRecord,
    DescriptiveTable,
    DocumentSpec,
    FigureInput,
    NarrativeMode,
    ResultsDocxError,
    RowType,
    SourceFile,
)


COEF_ALIASES: dict[str, tuple[str, ...]] = {
    "term": ("term",),
    "term_label": ("term_label",),
    "estimate": ("estimate", "coef"),
    "std_error": ("std.error", "std_error", "se", "Std. Error"),
    "p_value": ("p.value", "pvalue", "p", "Pr(>|t|)"),
    "model_id": ("model_id", "model"),
    "model_label": ("model_label",),
    "row_type": ("row_type",),
    "value_text": ("value_text",),
    "nobs": ("nobs", "N"),
    "adj_r_squared": ("adj.r.squared", "adj_r_squared", "adj.R2"),
    "dependent_variable": ("dependent_variable",),
    "fixed_effects": ("fixed_effects",),
    "cluster": ("cluster",),
    "controls": ("controls",),
    "panel": ("panel",),
}


def source_file(path: Path) -> SourceFile:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ResultsDocxError(f"Input file does not exist: {resolved}")
    digest = hashlib.sha256()
    with resolved.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return SourceFile(path=resolved, sha256=digest.hexdigest(), bytes=resolved.stat().st_size)


def load_document_spec(spec_path: Path) -> DocumentSpec:
    resolved_spec = spec_path.resolve()
    try:
        raw = json.loads(resolved_spec.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResultsDocxError(f"Cannot read build spec {resolved_spec}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ResultsDocxError("Build spec must be a JSON object")

    base = resolved_spec.parent
    narrative_mode = _narrative_mode(raw.get("narrative_mode", "standard"))
    coef_entries = _list_of_objects(raw, "coefficient_tables")
    if not coef_entries:
        raise ResultsDocxError("Build spec needs at least one coefficient table")
    descriptive_entries = _list_of_objects(raw, "descriptive_tables", required=False)
    figure_entries = _list_of_objects(raw, "figures", required=False)

    coefficient_tables = tuple(_load_coefficient_table(entry, base, narrative_mode) for entry in coef_entries)
    descriptive_tables = tuple(_load_descriptive_table(entry, base, narrative_mode) for entry in descriptive_entries)
    figures = tuple(_load_figure(entry, base, narrative_mode) for entry in figure_entries)

    run_id = _required_string(raw, "run_id")
    as_of_date = _required_string(raw, "as_of_date")
    if narrative_mode == "transport-only":
        _transport_identifier(run_id, resolved_spec, None, "run_id")
        _iso_date(as_of_date, resolved_spec, "as_of_date")

    return DocumentSpec(
        title=(
            _required_string(raw, "title")
            if narrative_mode == "standard"
            else _optional_string(raw, "title", "")
        ),
        subtitle=(
            _optional_string(raw, "subtitle", "Empirical results and audit pack")
            if narrative_mode == "standard"
            else _optional_string(raw, "subtitle", "")
        ),
        run_id=run_id,
        as_of_date=as_of_date,
        coefficient_tables=coefficient_tables,
        descriptive_tables=descriptive_tables,
        figures=figures,
        coefficient_decimals=_bounded_int(raw.get("coefficient_decimals", 3), "coefficient_decimals", 0, 8),
        descriptive_decimals=_bounded_int(raw.get("descriptive_decimals", 3), "descriptive_decimals", 0, 8),
        narrative_mode=narrative_mode,
    )


def _load_coefficient_table(
    entry: Mapping[str, Any],
    base: Path,
    narrative_mode: NarrativeMode,
) -> CoefficientTable:
    path = _resolve_input_path(base, _required_string(entry, "path"))
    source = source_file(path)
    rows = _read_csv(path)
    records: list[CoefficientRecord] = []
    seen_coef_keys: set[tuple[str, str, str]] = set()
    for source_row, row in rows:
        row_type_text = _alias_value(row, "row_type") or "coef"
        if row_type_text not in {"coef", "gof", "spec", "note"}:
            raise ResultsDocxError(f"{path}:{source_row}: unsupported row_type {row_type_text!r}")
        row_type: RowType = row_type_text  # type: ignore[assignment]
        term = _alias_value(row, "term")
        model_id = _alias_value(row, "model_id")
        if not term or not model_id:
            raise ResultsDocxError(f"{path}:{source_row}: term and model_id/model are required")
        if narrative_mode == "transport-only":
            _transport_identifier(term, path, source_row, "term")
            _transport_identifier(model_id, path, source_row, "model_id")
            panel = _alias_value(row, "panel")
            if panel:
                _transport_identifier(panel, path, source_row, "panel")

        estimate = _optional_float(_alias_value(row, "estimate"), path, source_row, "estimate")
        std_error = _optional_float(_alias_value(row, "std_error"), path, source_row, "std.error")
        p_value = _optional_float(_alias_value(row, "p_value"), path, source_row, "p.value")
        if row_type == "coef":
            missing = [
                name
                for name, value in (("estimate", estimate), ("std.error", std_error), ("p.value", p_value))
                if value is None
            ]
            if missing:
                raise ResultsDocxError(f"{path}:{source_row}: coefficient row missing {', '.join(missing)}")
            if p_value is not None and not 0 <= p_value <= 1:
                raise ResultsDocxError(f"{path}:{source_row}: p.value must be between 0 and 1")
            panel = _alias_value(row, "panel")
            key = (panel, term, model_id)
            if key in seen_coef_keys:
                raise ResultsDocxError(
                    f"{path}:{source_row}: duplicate coefficient for panel={panel!r}, term={term!r}, model={model_id!r}"
                )
            seen_coef_keys.add(key)

        nobs = _optional_int(_alias_value(row, "nobs"), path, source_row, "nobs")
        records.append(
            CoefficientRecord(
                source_row=source_row,
                term=term,
                term_label=_alias_value(row, "term_label") or _humanize(term),
                model_id=model_id,
                model_label=_alias_value(row, "model_label") or model_id,
                row_type=row_type,
                estimate=estimate,
                std_error=std_error,
                p_value=p_value,
                value_text=_alias_value(row, "value_text"),
                nobs=nobs,
                adj_r_squared=_optional_float(
                    _alias_value(row, "adj_r_squared"), path, source_row, "adj.r.squared"
                ),
                dependent_variable=_alias_value(row, "dependent_variable"),
                fixed_effects=_alias_value(row, "fixed_effects"),
                cluster=_alias_value(row, "cluster"),
                controls=_alias_value(row, "controls"),
                panel=_alias_value(row, "panel"),
            )
        )

    if not any(record.row_type == "coef" for record in records):
        raise ResultsDocxError(f"{path}: no coefficient rows found")
    _validate_model_metadata(records, path)
    primary_term = _none_or_string(entry.get("primary_term"), "primary_term")
    primary_model = _none_or_string(entry.get("primary_model"), "primary_model")
    if narrative_mode == "transport-only":
        if primary_term:
            _transport_identifier(primary_term, path, None, "primary_term")
        if primary_model:
            _transport_identifier(primary_model, path, None, "primary_model")
    return CoefficientTable(
        title=(
            _required_string(entry, "title")
            if narrative_mode == "standard"
            else _optional_string(entry, "title", "")
        ),
        source=source,
        records=tuple(records),
        primary_term=primary_term,
        primary_model=primary_model,
        note=_optional_string(entry, "note", ""),
    )


def _load_descriptive_table(
    entry: Mapping[str, Any],
    base: Path,
    narrative_mode: NarrativeMode,
) -> DescriptiveTable:
    path = _resolve_input_path(base, _required_string(entry, "path"))
    source = source_file(path)
    records: list[DescriptiveRecord] = []
    for source_row, row in _read_csv(path):
        variable = (row.get("variable") or "").strip()
        if not variable:
            raise ResultsDocxError(f"{path}:{source_row}: variable is required")
        if narrative_mode == "transport-only":
            _transport_identifier(variable, path, source_row, "variable")
        records.append(
            DescriptiveRecord(
                source_row=source_row,
                variable=variable,
                variable_label=(row.get("variable_label") or "").strip() or _humanize(variable),
                n=_optional_int((row.get("n") or "").strip(), path, source_row, "n"),
                mean=_optional_float((row.get("mean") or "").strip(), path, source_row, "mean"),
                sd=_optional_float((row.get("sd") or "").strip(), path, source_row, "sd"),
                p25=_optional_float((row.get("p25") or "").strip(), path, source_row, "p25"),
                p50=_optional_float((row.get("p50") or "").strip(), path, source_row, "p50"),
                p75=_optional_float((row.get("p75") or "").strip(), path, source_row, "p75"),
                minimum=_optional_float((row.get("min") or "").strip(), path, source_row, "min"),
                maximum=_optional_float((row.get("max") or "").strip(), path, source_row, "max"),
                sample=(row.get("sample") or "").strip(),
            )
        )
    if not records:
        raise ResultsDocxError(f"{path}: no descriptive-statistics rows found")
    return DescriptiveTable(
        title=(
            _required_string(entry, "title")
            if narrative_mode == "standard"
            else _optional_string(entry, "title", "")
        ),
        source=source,
        records=tuple(records),
        note=_optional_string(entry, "note", ""),
    )


def _load_figure(entry: Mapping[str, Any], base: Path, narrative_mode: NarrativeMode) -> FigureInput:
    path = _resolve_input_path(base, _required_string(entry, "path"))
    data_paths = entry.get("source_data")
    if not isinstance(data_paths, list) or not data_paths or not all(isinstance(item, str) for item in data_paths):
        raise ResultsDocxError("Each figure needs a non-empty source_data list for provenance")
    script_text = _none_or_string(entry.get("source_script"), "source_script")
    return FigureInput(
        title=(
            _required_string(entry, "title")
            if narrative_mode == "standard"
            else _optional_string(entry, "title", "")
        ),
        path=path,
        source=source_file(path),
        source_data=tuple(source_file(_resolve_input_path(base, item)) for item in data_paths),
        source_script=source_file(_resolve_input_path(base, script_text)) if script_text else None,
        alt_text=(
            _required_string(entry, "alt_text")
            if narrative_mode == "standard"
            else _optional_string(entry, "alt_text", "")
        ),
        note=_optional_string(entry, "note", ""),
        transport_figure=_boolean(entry.get("transport_figure", False), "transport_figure"),
    )


def _read_csv(path: Path) -> list[tuple[int, dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ResultsDocxError(f"{path}: CSV has no header")
            return [(index, {key: value or "" for key, value in row.items()}) for index, row in enumerate(reader, 2)]
    except UnicodeDecodeError as exc:
        raise ResultsDocxError(f"{path}: CSV must be UTF-8") from exc


def _validate_model_metadata(records: Sequence[CoefficientRecord], path: Path) -> None:
    fields = ("model_label", "nobs", "adj_r_squared", "dependent_variable", "fixed_effects", "cluster", "controls")
    for model_id in _first_seen(record.model_id for record in records):
        model_rows = [record for record in records if record.model_id == model_id and record.row_type == "coef"]
        for field in fields:
            values = {getattr(record, field) for record in model_rows if getattr(record, field) not in (None, "")}
            if len(values) > 1:
                raise ResultsDocxError(f"{path}: inconsistent {field} values within model {model_id!r}: {sorted(values, key=str)}")


def _alias_value(row: Mapping[str, str], canonical: str) -> str:
    for name in COEF_ALIASES[canonical]:
        value = row.get(name, "").strip()
        if value:
            return value
    return ""


def _optional_float(value: str, path: Path, row: int, field: str) -> float | None:
    if not value or value.upper() == "NA":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ResultsDocxError(f"{path}:{row}: {field} must be numeric, got {value!r}") from exc


def _optional_int(value: str, path: Path, row: int, field: str) -> int | None:
    number = _optional_float(value, path, row, field)
    if number is None:
        return None
    if not number.is_integer():
        raise ResultsDocxError(f"{path}:{row}: {field} must be an integer, got {value!r}")
    return int(number)


def _resolve_input_path(base: Path, text: str) -> Path:
    path = Path(text).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _required_string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ResultsDocxError(f"Build spec field {key!r} must be a non-empty string")
    return value.strip()


def _optional_string(data: Mapping[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ResultsDocxError(f"Build spec field {key!r} must be a string")
    return value.strip()


def _none_or_string(value: Any, key: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ResultsDocxError(f"Build spec field {key!r} must be a string or null")
    return value.strip() or None


def _list_of_objects(data: Mapping[str, Any], key: str, *, required: bool = True) -> list[Mapping[str, Any]]:
    value = data.get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ResultsDocxError(f"Build spec field {key!r} must be a list of objects")
    return value


def _bounded_int(value: Any, key: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ResultsDocxError(f"Build spec field {key!r} must be an integer from {minimum} to {maximum}")
    return value


def _boolean(value: Any, key: str) -> bool:
    if not isinstance(value, bool):
        raise ResultsDocxError(f"Build spec field {key!r} must be a boolean")
    return value


def _narrative_mode(value: Any) -> NarrativeMode:
    if not isinstance(value, str):
        raise ResultsDocxError("Build spec field 'narrative_mode' must be a string")
    normalized = value.strip().lower()
    if normalized == "engineering-smoke":
        normalized = "transport-only"
    if normalized not in {"standard", "transport-only"}:
        raise ResultsDocxError(
            "Build spec field 'narrative_mode' must be 'standard', 'transport-only', or 'engineering-smoke'"
        )
    return cast(NarrativeMode, normalized)


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().title()


_TRANSPORT_IDENTIFIER = re.compile(r"[A-Za-z0-9_.:+()/\-]{1,128}\Z")


def _transport_identifier(
    value: str,
    path: Path,
    source_row: int | None,
    field: str,
) -> None:
    if not _TRANSPORT_IDENTIFIER.fullmatch(value):
        location = f"{path}:{source_row}" if source_row is not None else str(path)
        raise ResultsDocxError(
            f"{location}: transport-only {field} must be a 1-128 character ASCII identifier"
        )


def _iso_date(value: str, path: Path, field: str) -> None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ResultsDocxError(f"{path}: transport-only {field} must be an ISO date (YYYY-MM-DD)") from exc
    if parsed.isoformat() != value:
        raise ResultsDocxError(f"{path}: transport-only {field} must be an ISO date (YYYY-MM-DD)")


def _first_seen(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))
