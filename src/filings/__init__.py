"""SEC regulatory filing discovery, document parsing, statement extraction, and AI footnote analysis.

Provides modular capabilities for SEC EDGAR integration, official US-GAAP taxonomy extraction,
institutional footnote disclosure analysis, and auditable statement approval into project records.
"""

from src.filings.ai_analyzer import FootnoteAiAnalyzer
from src.filings.edgar_client import SecEdgarClient
from src.filings.extractor import StatementExtractor
from src.filings.models import (
    ExtractedStatementItem,
    FilingAnalysisBundle,
    FilingFormType,
    FilingMetadata,
    FootnoteCategory,
    FootnoteObservationData,
    ObservationReviewStatus,
)
from src.filings.parser import FilingParser
from src.filings.services import FilingService

__all__ = [
    "FootnoteAiAnalyzer",
    "SecEdgarClient",
    "StatementExtractor",
    "FilingParser",
    "FilingService",
    "FilingFormType",
    "FootnoteCategory",
    "ObservationReviewStatus",
    "FilingMetadata",
    "ExtractedStatementItem",
    "FootnoteObservationData",
    "FilingAnalysisBundle",
]
