"""Shared pytest fixtures for AI Amazon Fee Auditor tests."""
import pytest


@pytest.fixture
def sample_pbi_rows():
    """
    Four rows mimicking the Power BI executeQueries JSON response format.

    Column keys use the PBI fully-qualified format:
      fact_fee_preview[key_sales_marketplace_sku]
      [YEAR]
      [WEEKNUM]
      [avg_fee_per_unit]

    Two keys: a normal SKU key and an amzn.gr.* grouping code.
    ISO year 2026, weeks 1 and 2.
    """
    return [
        {
            "fact_fee_preview[key_sales_marketplace_sku]": "US | US-OHFB-001",
            "[YEAR]": 2026,
            "[WEEKNUM]": 1,
            "[avg_fee_per_unit]": 1.50,
        },
        {
            "fact_fee_preview[key_sales_marketplace_sku]": "US | US-OHFB-001",
            "[YEAR]": 2026,
            "[WEEKNUM]": 2,
            "[avg_fee_per_unit]": 2.50,
        },
        {
            "fact_fee_preview[key_sales_marketplace_sku]": "amzn.gr.ABCD1234",
            "[YEAR]": 2026,
            "[WEEKNUM]": 1,
            "[avg_fee_per_unit]": 3.00,
        },
        {
            "fact_fee_preview[key_sales_marketplace_sku]": "amzn.gr.ABCD1234",
            "[YEAR]": 2026,
            "[WEEKNUM]": 2,
            "[avg_fee_per_unit]": 3.10,
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
