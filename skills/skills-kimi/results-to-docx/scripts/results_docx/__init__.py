"""Auditable empirical-results DOCX builder."""

from .model import BuildRequest, BuildResult, ResultsDocxError
from .pipeline import build_results_pack

__all__ = ["BuildRequest", "BuildResult", "ResultsDocxError", "build_results_pack"]
