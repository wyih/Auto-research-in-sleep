"""One-call pipeline: validate inputs, build DOCX, normalize identity, write audits."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from author_identity import OfficeAuthorError, validate_office_author
from normalize_docx_author import audit_docx, normalize_docx

from .document import compose_document, embedded_figures
from .inputs import load_document_spec, source_file
from .model import BuildRequest, BuildResult, DocumentSpec, NarrativeClaim, ResultsDocxError, SourceFile


BUILDER_VERSION = "1.3.0"


def build_results_pack(request: BuildRequest) -> BuildResult:
    try:
        author = validate_office_author(request.author)
    except OfficeAuthorError as error:
        raise ResultsDocxError(str(error)) from error
    output = request.output_path.expanduser().resolve()
    _validate_output_target(output)
    manifest = (request.manifest_path or output.parent / "RESULTS_DOCX_MANIFEST.md").expanduser().resolve()
    receipt = (request.receipt_path or output.parent / "RESULTS_DOCX_RECEIPT.json").expanduser().resolve()
    _validate_auxiliary_target(manifest, expected_suffix=".md")
    _validate_auxiliary_target(receipt, expected_suffix=".json")
    if len({output, manifest, receipt}) != 3:
        raise ResultsDocxError("DOCX, manifest, and receipt paths must be distinct")
    _guard_existing((output, manifest, receipt), force=request.force)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)

    spec = load_document_spec(request.spec_path)
    included_figures = embedded_figures(spec)
    inputs = _collect_inputs(request.spec_path, spec)
    input_paths = {item.path for item in inputs}
    collisions = input_paths & {output, manifest, receipt}
    if collisions:
        raise ResultsDocxError("Refusing to overwrite an input artifact: " + ", ".join(map(str, sorted(collisions))))
    document, claims = compose_document(spec, author=author)

    fd, temp_name = tempfile.mkstemp(prefix=f".{output.stem}.", suffix=".docx", dir=output.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        document.save(temp_path)
        normalize_docx(temp_path, author)
        temp_audit = audit_docx(temp_path, author)
        if not temp_audit["passed"]:
            raise ResultsDocxError(f"Office identity normalization failed: {temp_audit}")
        os.replace(temp_path, output)
    finally:
        temp_path.unlink(missing_ok=True)

    final_audit = audit_docx(output, author)
    if not final_audit["passed"]:
        raise ResultsDocxError(f"Final Office identity audit failed: {final_audit}")

    output_source = source_file(output)
    receipt_payload = _receipt_payload(
        request=request,
        spec=spec,
        output=output_source,
        manifest_path=manifest,
        receipt_path=receipt,
        inputs=inputs,
        claims=claims,
        metadata_audit=final_audit,
    )
    _atomic_write_text(manifest, _manifest_markdown(receipt_payload))
    _atomic_write_text(receipt, json.dumps(receipt_payload, ensure_ascii=False, indent=2) + "\n")

    return BuildResult(
        output_path=output,
        manifest_path=manifest,
        receipt_path=receipt,
        output_sha256=output_source.sha256,
        output_bytes=output_source.bytes,
        table_count=len(spec.coefficient_tables) + len(spec.descriptive_tables),
        figure_count=len(included_figures),
        narrative_claim_count=len(claims),
        narrative_mode=spec.narrative_mode,
        metadata_audit=final_audit,
    )


def _validate_output_target(output: Path) -> None:
    if output.suffix.lower() != ".docx":
        raise ResultsDocxError("Output path must end in .docx")
    parts = {part.lower().replace("-", "_") for part in output.parts}
    forbidden = {"paper", "papers", "manuscript", "submission", "submissions"}
    if parts & forbidden:
        raise ResultsDocxError(f"Refusing to write a results pack inside a manuscript path: {output}")
    if "results_docx" not in parts:
        raise ResultsDocxError("Output path must include a dedicated results_docx directory")


def _validate_auxiliary_target(path: Path, *, expected_suffix: str) -> None:
    if path.suffix.lower() != expected_suffix:
        raise ResultsDocxError(f"Auxiliary output must end in {expected_suffix}: {path}")
    forbidden = {"paper", "papers", "manuscript", "submission", "submissions"}
    if {part.lower() for part in path.parts} & forbidden:
        raise ResultsDocxError(f"Refusing to write an audit artifact inside a manuscript path: {path}")


def _guard_existing(paths: tuple[Path, ...], *, force: bool) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing and not force:
        raise ResultsDocxError("Refusing to overwrite existing output without --force: " + ", ".join(existing))


def _collect_inputs(spec_path: Path, spec: DocumentSpec) -> tuple[SourceFile, ...]:
    sources = [source_file(spec_path)]
    sources.extend(table.source for table in spec.coefficient_tables)
    sources.extend(table.source for table in spec.descriptive_tables)
    for figure in spec.figures:
        sources.append(figure.source)
        sources.extend(figure.source_data)
        if figure.source_script:
            sources.append(figure.source_script)
    by_path = {source.path: source for source in sources}
    return tuple(by_path[path] for path in sorted(by_path, key=str))


def _receipt_payload(
    *,
    request: BuildRequest,
    spec: DocumentSpec,
    output: SourceFile,
    manifest_path: Path,
    receipt_path: Path,
    inputs: tuple[SourceFile, ...],
    claims: tuple[NarrativeClaim, ...],
    metadata_audit: dict[str, object],
) -> dict[str, Any]:
    included_figures = embedded_figures(spec)
    figure_receipts = _figure_receipts(spec)
    return {
        "schema_version": 1,
        "builder": "results-to-docx",
        "builder_version": BUILDER_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": spec.run_id,
        "narrative_mode": spec.narrative_mode,
        "document": {
            "path": str(output.path),
            "sha256": output.sha256,
            "bytes": output.bytes,
            "tables": len(spec.coefficient_tables) + len(spec.descriptive_tables),
            "figures": len(included_figures),
            "narrative_claims": len(claims),
        },
        "outputs": {"manifest": str(manifest_path), "receipt": str(receipt_path)},
        "inputs": [
            {"path": str(item.path), "sha256": item.sha256, "bytes": item.bytes}
            for item in inputs
        ],
        "tables": [
            {
                "kind": "coefficient",
                "title": (
                    f"Coefficient output C{index}"
                    if spec.narrative_mode == "transport-only"
                    else table.title
                ),
                "source": str(table.source.path),
                "sha256": table.source.sha256,
                "rows": len(table.records),
            }
            for index, table in enumerate(spec.coefficient_tables, 1)
        ]
        + [
            {
                "kind": "descriptive",
                "title": (
                    f"Descriptive output D{index}"
                    if spec.narrative_mode == "transport-only"
                    else table.title
                ),
                "source": str(table.source.path),
                "sha256": table.source.sha256,
                "rows": len(table.records),
            }
            for index, table in enumerate(spec.descriptive_tables, 1)
        ],
        "figures": figure_receipts,
        "narrative_claims": [
            {
                "text": claim.text,
                "source_path": str(claim.source_path),
                "source_row": claim.source_row,
                "selectors": claim.selectors,
                "values": claim.values,
            }
            for claim in claims
        ],
        "metadata": metadata_audit,
        "design": {
            "base_preset": "standard_business_brief",
            "named_overrides": ["academic_serif", "academic_three_line_tables"],
            "page": "US Letter portrait",
            "margins_inches": 1.0,
            "usable_width_dxa": 9360,
            "table_indent_dxa": 120,
            "table_rules": "top/header/bottom only; no vertical rules",
        },
        "safety": {
            "manuscript_files_modified": False,
            "output_directory_guard": "results_docx",
            "force_overwrite": request.force,
        },
        "transport_policy": (
            {
                "structured_output_only": True,
                "raw_identifier_fields": ["term", "model_id", "panel", "variable", "run_id"],
                "ignored_free_text_fields": [
                    "title",
                    "subtitle",
                    "table.title",
                    "table.note",
                    "term_label",
                    "model_label",
                    "dependent_variable",
                    "fixed_effects",
                    "cluster",
                    "controls",
                    "value_text",
                    "variable_label",
                    "sample",
                    "figure.title",
                    "figure.note",
                    "figure.alt_text",
                ],
                "figures_default_embedded": False,
                "explicit_transport_figure_required": True,
                "embedded_image_pixels_semantically_audited": False,
            }
            if spec.narrative_mode == "transport-only"
            else None
        ),
    }


def _figure_receipts(spec: DocumentSpec) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    embedded_index = 0
    for declared_index, figure in enumerate(spec.figures, 1):
        embedded = spec.narrative_mode == "standard" or figure.transport_figure
        if embedded:
            embedded_index += 1
        if spec.narrative_mode == "transport-only":
            title = f"Transport figure F{embedded_index}" if embedded else f"Excluded figure X{declared_index}"
            alt_text = (
                f"Transported figure F{embedded_index}. Image pixels are not semantically audited."
                if embedded
                else None
            )
        else:
            title = figure.title
            alt_text = figure.alt_text
        receipts.append(
            {
                "title": title,
                "path": str(figure.path),
                "sha256": figure.source.sha256,
                "source_data": [str(item.path) for item in figure.source_data],
                "source_script": str(figure.source_script.path) if figure.source_script else None,
                "alt_text": alt_text,
                "embedded": embedded,
                "image_pixels_semantically_audited": False,
            }
        )
    return receipts


def _manifest_markdown(payload: dict[str, Any]) -> str:
    document = payload["document"]
    metadata = payload["metadata"]
    lines = [
        "# Results Docx Manifest",
        "",
        "## Document",
        f"- path: `{document['path']}`",
        f"- run_id: `{payload['run_id']}`",
        f"- narrative_mode: `{payload['narrative_mode']}`",
        f"- sha256: `{document['sha256']}`",
        f"- bytes: `{document['bytes']}`",
        f"- tables: `{document['tables']}`",
        f"- figures: `{document['figures']}`",
        "",
        "## Inputs",
        "| Artifact | SHA-256 | Bytes |",
        "|---|---|---:|",
    ]
    for item in payload["inputs"]:
        lines.append(f"| `{item['path']}` | `{item['sha256']}` | {item['bytes']} |")
    lines.extend(
        [
            "",
            "## Tables In Document",
            "| Kind | Title | Source | Rows |",
            "|---|---|---|---:|",
        ]
    )
    for table in payload["tables"]:
        lines.append(f"| {table['kind']} | {table['title']} | `{table['source']}` | {table['rows']} |")
    lines.extend(
        [
            "",
            "## Figures In Document",
            "| Title | Embedded | Figure | Source data |",
            "|---|---|---|---|",
        ]
    )
    if payload["figures"]:
        for figure in payload["figures"]:
            data = ", ".join(f"`{item}`" for item in figure["source_data"])
            lines.append(
                f"| {figure['title']} | {str(figure['embedded']).lower()} | `{figure['path']}` | {data} |"
            )
    else:
        lines.append("| None | - | - | - |")
    lines.extend(
        [
            "",
            "## Narrative Claim Provenance",
            "| Claim | Source row | Selectors |",
            "|---|---|---|",
        ]
    )
    for claim in payload["narrative_claims"]:
        selectors = json.dumps(claim["selectors"], ensure_ascii=False, sort_keys=True)
        lines.append(f"| {claim['text']} | `{claim['source_path']}:{claim['source_row']}` | `{selectors}` |")
    lines.extend(
        [
            "",
            "## Metadata",
            f"- author: `{metadata['creator']}`",
            f"- last_modified_by: `{metadata['lastModifiedBy']}`",
            f"- company: `{metadata['company']}`",
            f"- manager: `{metadata['manager']}`",
            f"- metadata_audit_passed: `{str(metadata['passed']).lower()}`",
            "",
            "## Design",
            "- base preset: `standard_business_brief`",
            "- named overrides: `academic_serif`, `academic_three_line_tables`",
            "- explicit table geometry: `9360 DXA`; table indent: `120 DXA`",
            "",
            "## Non-Goals",
            "- manuscript files modified: **no**",
            "- analysis models re-estimated: **no**",
            "",
        ]
    )
    return "\n".join(lines)


def _atomic_write_text(path: Path, text: str) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(text, encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)
