"""Shared pytest fixtures for AI Amazon Fee Auditor tests."""
import pytest


@pytest.fixture
def sample_pbi_rows():
    """
    Four rows mimicking the Power BI executeQueries JSON response format.

    Column keys use the PBI fully-qualified format returned by the live API:
      fact_fee_preview[key_sales_marketplace_sku]
      fact_fee_preview[date_fee_preview]
      [avg_fee_per_unit]

    YEAR and WEEKNUM are no longer DAX aliases — they are derived in Python
    by process_pbi_rows() from date_fee_preview via isocalendar().

    Two keys: a normal US SKU key and an amzn.gr.* grouping code.
    Dates are in ISO week 1 and 2 of 2026.
    """
    return [
        {
            "fact_fee_preview[key_sales_marketplace_sku]": "US | US-OHFB-001",
            "fact_fee_preview[date_fee_preview]": "2025-12-29T00:00:00",  # ISO 2026-W01 Monday
            "fact_fee_preview[avg_fee_per_unit]": 2.00,
        },
        {
            "fact_fee_preview[key_sales_marketplace_sku]": "US | US-OHFB-001",
            "fact_fee_preview[date_fee_preview]": "2026-01-05T00:00:00",  # ISO 2026-W02 Monday
            "fact_fee_preview[avg_fee_per_unit]": 2.50,
        },
        {
            "fact_fee_preview[key_sales_marketplace_sku]": "amzn.gr.ABCD1234",
            "fact_fee_preview[date_fee_preview]": "2025-12-29T00:00:00",  # ISO 2026-W01 Monday
            "fact_fee_preview[avg_fee_per_unit]": 3.00,
        },
        {
            "fact_fee_preview[key_sales_marketplace_sku]": "amzn.gr.ABCD1234",
            "fact_fee_preview[date_fee_preview]": "2026-01-05T00:00:00",  # ISO 2026-W02 Monday
            "fact_fee_preview[avg_fee_per_unit]": 3.10,
        },
    ]


@pytest.fixture
def sample_sku_rows():
    """
    Rows mimicking the SKUs DAX response.

    Keys: SKUs[Key Column: Country | SKU], SKUs[SKU], SKUs[ASIN], SKUs[Sales Region].
    One row for the normal key; amzn.gr.* keys deliberately absent (they won't join).
    """
    return [
        {
            "SKUs[Key Column: Country | SKU]": "US | US-OHFB-001",
            "SKUs[SKU]": "US-OHFB-001",
            "SKUs[ASIN]": "B0EXAMPLE01",
            "SKUs[Sales Region]": "US",
        },
    ]
