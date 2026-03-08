"""
GovLens Data Models

Pydantic v2 models for contracts, institutions, vendors,
filter state, and aggregation results.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class Contract(BaseModel):
    """
    Represents a single government contract record.

    Combines fields from the CRZ scraper's listing page, detail page,
    PDF extraction, and GovLens-specific enrichment fields.
    """

    # ── Listing-page fields ──────────────────────────────────────────
    published_day: Optional[str] = None
    published_month: Optional[str] = None
    published_year: Optional[str] = None
    published_date: Optional[str] = Field(
        default=None, description="ISO date (YYYY-MM-DD) of publication"
    )
    contract_title: Optional[str] = None
    contract_number: Optional[str] = None
    price_raw: Optional[str] = None
    price_numeric_eur: Optional[float] = Field(
        default=None, description="Parsed price in EUR"
    )
    supplier: Optional[str] = None
    buyer: Optional[str] = None
    contract_url: Optional[str] = None
    contract_id: Optional[str] = None
    scraped_at: Optional[str] = Field(
        default=None, description="ISO datetime when the record was scraped"
    )

    # ── Detail-page fields ───────────────────────────────────────────
    contract_number_detail: Optional[str] = None
    contract_id_detail: Optional[str] = None
    buyer_detail: Optional[str] = None
    supplier_detail: Optional[str] = None
    ico_buyer: Optional[str] = Field(
        default=None, description="IČO (company ID) of the buyer"
    )
    ico_supplier: Optional[str] = Field(
        default=None, description="IČO (company ID) of the supplier"
    )
    date_published: Optional[str] = None
    date_concluded: Optional[str] = None
    date_effective: Optional[str] = None
    date_valid_until: Optional[str] = None

    # ── PDF fields ───────────────────────────────────────────────────
    pdf_urls: Optional[List[str]] = None
    pdf_url: Optional[str] = None
    pdf_local_path: Optional[str] = None
    pdf_text: Optional[str] = Field(
        default=None, description="Extracted text from the PDF (truncated at 50k chars)"
    )

    # ── GovLens enrichment fields (Phase 0) ──────────────────────────
    category: str = Field(
        default="not_decided",
        description="LLM-assigned service category (placeholder: 'not_decided')",
    )
    pdf_text_summary: str = Field(
        default="not_summarized",
        description="LLM-generated summary of pdf_text (placeholder: 'not_summarized')",
    )
    award_type: str = Field(
        default="unknown",
        description="Award type: tendered | direct_award | negotiated | unknown",
    )

    model_config = {"extra": "allow"}


class Institution(BaseModel):
    """Represents a buying institution (Objednávateľ)."""

    name: str
    ico: Optional[str] = None
    contract_count: int = 0
    total_spend: float = 0.0


class Vendor(BaseModel):
    """Represents a supplier / vendor (Dodávateľ)."""

    name: str
    ico: Optional[str] = None
    contract_count: int = 0
    total_spend: float = 0.0


class FilterState(BaseModel):
    """
    Encodes the shared global filter state used across all UI modes.
    All fields are optional; ``None`` means "no filter applied".
    """

    institutions: Optional[List[str]] = Field(
        default=None, description="Selected institution name(s)"
    )
    date_from: Optional[str] = Field(
        default=None, description="Start of date range (ISO YYYY-MM-DD)"
    )
    date_to: Optional[str] = Field(
        default=None, description="End of date range (ISO YYYY-MM-DD)"
    )
    categories: Optional[List[str]] = Field(
        default=None, description="Selected category value(s)"
    )
    vendors: Optional[List[str]] = Field(
        default=None, description="Selected vendor/supplier name(s)"
    )
    institution_icos: Optional[List[str]] = Field(
        default=None, description="Selected IČO value(s) for institutions (ico_buyer)"
    )
    vendor_icos: Optional[List[str]] = Field(
        default=None, description="Selected IČO value(s) for vendors (ico_supplier)"
    )
    icos: Optional[List[str]] = Field(
        default=None, description="Deprecated: selected ICO value(s) for buyer or supplier"
    )
    value_min: Optional[float] = Field(
        default=None, description="Minimum contract value (EUR)"
    )
    value_max: Optional[float] = Field(
        default=None, description="Maximum contract value (EUR)"
    )
    award_types: Optional[List[str]] = Field(
        default=None,
        description="Selected award types (tendered / direct_award / negotiated / unknown)",
    )
    text_search: Optional[str] = Field(
        default=None, description="Free-text search over title and summary"
    )


class AggregationResult(BaseModel):
    """Result of a group-by + aggregation operation."""

    group_key: str = Field(description="Field that was grouped by (e.g. 'category')")
    group_value: str = Field(description="Value of the group (e.g. 'construction')")
    contract_count: int = 0
    total_spend: float = 0.0
    avg_value: float = 0.0
    max_value: float = 0.0
