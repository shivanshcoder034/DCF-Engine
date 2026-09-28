"""Service layer coordinating SEC filing persistence, document retrieval, and historical statement import.

Bridges SEC EDGAR client, parsers, and AI analyzers with the application's
database persistence models and valuation project workspaces.
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from src.data.database import get_db_session
from src.data.models import Company, FilingObservation, ImportBatch, SecFiling, ValuationProject
from src.data.services import FinancialDataService
from src.filings.ai_analyzer import FootnoteAiAnalyzer
from src.filings.edgar_client import SecEdgarClient
from src.filings.extractor import StatementExtractor, date_from_str
from src.filings.models import (
    ExtractedStatementItem,
    FilingAnalysisBundle,
    FilingMetadata,
    FootnoteObservationData,
)
from src.filings.parser import FilingParser

logger = logging.getLogger(__name__)


class FilingService:
    """Coordinates filing discovery, document parsing, AI footnote analysis, and historical data approval."""

    def __init__(self) -> None:
        self.edgar_client = SecEdgarClient()
        self.parser = FilingParser()
        self.extractor = StatementExtractor()
        self.analyzer = FootnoteAiAnalyzer()

    # ---------------- Discovery & Ingestion ----------------

    def discover_filings(
        self,
        ticker_or_cik: str,
        forms: Optional[List[str]] = None,
        limit: int = 30,
    ) -> Tuple[Optional[Dict[str, Any]], List[FilingMetadata]]:
        """Look up entity info and discover recent 10-K and 10-Q filings.

        Returns (company_info_dict, list_of_filing_metadata).
        """
        entity_info = self.edgar_client.lookup_cik(ticker_or_cik)
        if not entity_info:
            return None, []

        cik = entity_info["cik"]
        filings = self.edgar_client.get_company_filings(cik, forms=forms, limit=limit)
        return entity_info, filings

    def retrieve_and_analyze_filing(
        self,
        filing: FilingMetadata,
        selected_categories: Optional[List[str]] = None,
    ) -> FilingAnalysisBundle:
        """Retrieve filing document, parse sections, extract statement facts, and generate AI observations."""
        bundle = FilingAnalysisBundle(filing=filing)

        # 1. Fetch document text / HTML
        raw_content: Optional[str] = None
        try:
            raw_content = self.edgar_client.get_filing_document(filing)
        except Exception as exc:
            bundle.diagnostic_notes.append(f"Warning: Primary filing document download failed: {exc}")

        # 2. Fetch official US-GAAP facts via SEC company facts API
        company_facts = self.edgar_client.get_company_facts(filing.cik)
        if company_facts:
            bundle.extracted_items = self.extractor.extract_from_company_facts(company_facts, filing)
        else:
            bundle.diagnostic_notes.append("Notice: Official SEC XBRL facts were unavailable; using document parser fallback.")

        # 3. Parse footnote sections from raw content
        parsed_sections: Dict[str, Dict[str, Any]] = {}
        full_text = ""
        if raw_content:
            parsed = self.parser.extract_text_and_sections(raw_content)
            parsed_sections = parsed.get("sections", {})
            full_text = parsed.get("plain_text", "")
            for sec_key, sec_data in parsed_sections.items():
                bundle.footnote_sections[sec_data["title"]] = sec_data["text"]

        # 4. Run AI / NLP footnote analysis
        bundle.observations = self.analyzer.analyze_filing(
            filing=filing,
            parsed_sections=parsed_sections,
            full_text=full_text,
            selected_categories=selected_categories,
        )

        filing.status = "Analyzed"
        return bundle

    # ---------------- Database Persistence ----------------

    @staticmethod
    def save_or_update_filing(metadata: FilingMetadata, company_id: Optional[int] = None) -> SecFiling:
        """Persist or update an SEC filing record in the database."""
        with get_db_session() as session:
            existing = session.query(SecFiling).filter(
                SecFiling.accession_number == metadata.accession_number
            ).first()

            filing_date_obj = date_from_str(metadata.filing_date)
            report_date_obj = date_from_str(metadata.report_date)

            if existing:
                existing.status = metadata.status
                existing.local_cache_path = metadata.local_cache_path
                existing.primary_doc_url = metadata.primary_doc_url
                if company_id:
                    existing.company_id = company_id
                session.flush()
                metadata.id = existing.id
                return existing

            record = SecFiling(
                company_id=company_id or metadata.company_id,
                ticker=metadata.ticker,
                cik=metadata.cik,
                company_name=metadata.company_name,
                form_type=metadata.form_type,
                accession_number=metadata.accession_number,
                filing_date=filing_date_obj,
                report_date=report_date_obj,
                fiscal_year=metadata.fiscal_year,
                fiscal_period=metadata.fiscal_period,
                primary_document=metadata.primary_document,
                primary_doc_url=metadata.primary_doc_url,
                local_cache_path=metadata.local_cache_path,
                status=metadata.status,
                is_amended=1 if metadata.is_amended else 0,
                amends_accession=metadata.amends_accession,
            )
            session.add(record)
            session.flush()
            metadata.id = record.id
            return record

    @staticmethod
    def save_observations(filing_id: int, observations: List[FootnoteObservationData]) -> int:
        """Persist or refresh footnote observations associated with a filing."""
        with get_db_session() as session:
            # Clear previous observations for clean re-analysis
            session.query(FilingObservation).filter(FilingObservation.filing_id == filing_id).delete()

            count = 0
            for obs in observations:
                record = FilingObservation(
                    filing_id=filing_id,
                    category=obs.category,
                    summary=obs.summary,
                    source_section=obs.source_section,
                    source_location=obs.source_location,
                    source_quote=obs.source_quote,
                    explicit_facts=obs.explicit_facts,
                    potential_implications=obs.potential_implications,
                    confidence_score=obs.confidence_score,
                    review_status=obs.review_status,
                    user_notes=obs.user_notes,
                )
                session.add(record)
                count += 1
            session.flush()
            return count

    @staticmethod
    def update_observation_status(
        observation_id: int,
        review_status: str,
        user_notes: Optional[str] = None,
    ) -> bool:
        """Update user review status and audit notes on an observation."""
        with get_db_session() as session:
            obs = session.query(FilingObservation).filter(FilingObservation.id == observation_id).first()
            if not obs:
                return False
            obs.review_status = review_status
            if user_notes is not None:
                obs.user_notes = user_notes
            obs.updated_at = datetime.utcnow()
            session.flush()
            return True

    @staticmethod
    def list_saved_filings(company_id: Optional[int] = None, ticker: Optional[str] = None) -> List[SecFiling]:
        """List previously saved filings from SQLite."""
        with get_db_session() as session:
            q = session.query(SecFiling)
            if company_id is not None:
                q = q.filter(SecFiling.company_id == company_id)
            if ticker:
                q = q.filter(SecFiling.ticker == ticker.upper())
            return q.order_by(SecFiling.report_date.desc()).all()

    @staticmethod
    def get_filing_observations(filing_id: int) -> List[FilingObservation]:
        """Retrieve stored observations for a filing."""
        with get_db_session() as session:
            return session.query(FilingObservation).filter(
                FilingObservation.filing_id == filing_id
            ).order_by(FilingObservation.id.asc()).all()

    # ---------------- Historical Statement Approval Workflow ----------------

    @staticmethod
    def approve_and_import_statements(
        project_id: int,
        filing: FilingMetadata,
        selected_items: List[ExtractedStatementItem],
        conflict_resolution: str = "skip",  # "skip" or "overwrite"
    ) -> Tuple[ImportBatch, int, int]:
        """Approve and import verified statement data points into historical project records.

        Atomically creates an ImportBatch with full audit provenance and persists
        FinancialDataPoint records without mutating existing valuation models.
        """
        valid_records: List[Dict[str, Any]] = []

        for item in selected_items:
            rec = {
                "statement_type": item.statement_type,
                "line_item_code": item.line_item_code,
                "display_name": item.display_name,
                "period_start_date": date_from_str(item.period_start_date),
                "period_end_date": date_from_str(item.period_end_date),
                "period_type": item.period_type,
                "value": float(item.value),
                "currency": item.currency,
                "unit": item.unit,
                "data_classification": "reported_actual",
                "source_type": "sec_filing",
                "source_reference": f"SEC {filing.form_type} (Accession: {filing.accession_number})",
                "source_reporting_date": date_from_str(filing.report_date),
            }
            valid_records.append(rec)

        filename = f"SEC_{filing.form_type}_{filing.ticker or filing.cik}_{filing.report_date}.filing"
        source_description = (
            f"SEC EDGAR Filing Ingestion: Form {filing.form_type}, Period Ending {filing.report_date}, "
            f"Filed {filing.filing_date}, Accession {filing.accession_number}."
        )

        batch, saved_count, updated_count = FinancialDataService.save_import_batch(
            project_id=project_id,
            filename=filename,
            valid_records=valid_records,
            rejected_count=0,
            source_description=source_description,
            conflict_resolution=conflict_resolution,
        )

        return batch, saved_count, updated_count
