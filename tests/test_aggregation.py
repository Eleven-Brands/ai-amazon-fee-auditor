"""
Unit tests for explore_fees.py — all 8 tests mapped in VALIDATION.md.

These tests are intentionally RED (ImportError) until Wave 2 creates explore_fees.py.
Do NOT skip or mark xfail — the tests must fail naturally to enforce TDD discipline.

Requirements covered: DATA-01, DATA-02, DETECT-01
"""
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

import datetime

from pydantic import ValidationError

from explore_fees import (
    run_dax,
    process_pbi_rows,
    validate_value_count,
    extract_country,
    get_currency_for_country,
    build_output_df,
    iso_to_week_start,
    validate_output_df,
)


# ---------------------------------------------------------------------------
# DATA-01: Power BI query shape and column contract
# ---------------------------------------------------------------------------


def test_run_dax_returns_expected_shape():
    """
    run_dax() must return a non-empty list of dicts given a valid PBI response.

    HTTP is mocked — no live credentials required.
    Validates: shape contract and that run_dax does not silently swallow errors.
    """
    mock_response_json = {
        "results": [
            {
                "tables": [
                    {
                        "rows": [
                            {
                                "fact_fee_preview[key_sales_marketplace_sku]": "US | US-OHFB-001",
                                "[YEAR]": 2026,
                                "[WEEKNUM]": 1,
                                "[avg_fee_per_unit]": 1.50,
                            },
                            {
                                "fact_fee_preview[key_sales_marketplace_sku]": "US | US-OHFB-002",
                                "[YEAR]": 2026,
                                "[WEEKNUM]": 1,
                                "[avg_fee_per_unit]": 2.75,
                            },
                        ]
                    }
                ]
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_json
    # Soft-error key is absent in mock_response_json (results[0] has no "error" key)
    # No override needed — dict.get("error") returns None naturally

    with patch("requests.post", return_value=mock_resp):
        result = run_dax(
            dax="EVALUATE TOPN(2, 'fact_fee_preview')",
            token="fake-bearer-token",
        )

    assert isinstance(result, list), "run_dax must return a list"
    assert len(result) > 0, "run_dax must return at least one row"
    assert isinstance(result[0], dict), "Each row must be a dict"


def test_weekly_avg_calculation(sample_pbi_rows):
    """
    process_pbi_rows() must rename PBI columns, preserve numeric type, and return a DataFrame.

    The DAX query already produces AVERAGE per week — this test validates column renaming
    and numeric dtype, not re-aggregation logic.

    Given two rows for "US | US-OHFB-001" (week 1: 1.50, week 2: 2.50),
    the output DataFrame must have an avg_fee_per_unit column with float values.
    """
    df = process_pbi_rows(sample_pbi_rows)

    assert isinstance(df, pd.DataFrame), "process_pbi_rows must return a DataFrame"
    assert "avg_fee_per_unit" in df.columns, "Column avg_fee_per_unit must exist"
    assert pd.api.types.is_float_dtype(df["avg_fee_per_unit"]), (
        "avg_fee_per_unit must be float dtype"
    )

    us_rows = df[df["key_sales_marketplace_sku"] == "US | US-OHFB-001"]
    assert len(us_rows) == 2, "Both week rows for US | US-OHFB-001 must be present"

    week1_fee = us_rows[us_rows["week_num"] == 1]["avg_fee_per_unit"].iloc[0]
    assert week1_fee == pytest.approx(1.50), (
        "Week 1 avg_fee_per_unit for US | US-OHFB-001 must be 1.50"
    )


# ---------------------------------------------------------------------------
# DATA-01: Value-count guard (abort before execution if > 1_000_000 cells)
# ---------------------------------------------------------------------------


def test_value_count_within_limit():
    """
    validate_value_count() must return the cell count when within limit,
    and raise ValueError when the projected cell count exceeds 1_000_000.

    Prevents runaway DAX queries that would time out or blow memory.
    """
    # 5,274 keys × 16 weeks × 5 cols = 421,920 — well within limit
    result = validate_value_count(n_keys=5274, n_weeks=16, n_cols=5)
    assert result < 1_000_000, (
        f"validate_value_count(5274, 16, 5) must return < 1_000_000, got {result}"
    )

    # 10,000 keys × 16 weeks × 10 cols = 1,600,000 — exceeds limit → must raise
    with pytest.raises(ValueError):
        validate_value_count(n_keys=10000, n_weeks=16, n_cols=10)


# ---------------------------------------------------------------------------
# DATA-02: Country and currency extraction
# ---------------------------------------------------------------------------


def test_country_extraction():
    """
    extract_country() must parse the 2-letter country prefix from key_sales_marketplace_sku.

    Format: "<CC> | <CC>-<SKU>" — the prefix before " | " is the country code.
    """
    df = pd.DataFrame({
        "key_sales_marketplace_sku": [
            "US | US-OHFB-001",
            "DE | DE-OHFB-002",
            "GB | GB-OHFB-003",
        ]
    })

    result = extract_country(df)

    assert "country" in result.columns, "extract_country must add a 'country' column"
    assert list(result["country"]) == ["US", "DE", "GB"], (
        "Country codes must match the prefix of key_sales_marketplace_sku"
    )


def test_currency_mapping_completeness():
    """
    get_currency_for_country() must cover all active OrganiHaus marketplaces.

    Known active marketplaces: US, CA, GB, MX, DE, FR, ES, IT.
    Unknown country codes must return 'UNKNOWN', not raise an exception.
    """
    active_countries = ["US", "CA", "GB", "MX", "DE", "FR", "ES", "IT"]

    for cc in active_countries:
        result = get_currency_for_country(cc)
        assert result != "UNKNOWN", (
            f"get_currency_for_country('{cc}') returned 'UNKNOWN' — mapping is incomplete"
        )

    unknown_result = get_currency_for_country("ZZ")
    assert unknown_result == "UNKNOWN", (
        "get_currency_for_country('ZZ') must return 'UNKNOWN' for unrecognised country codes"
    )


# ---------------------------------------------------------------------------
# DETECT-01: amzn.gr.* key handling, CSV schema, ISO week helper
# ---------------------------------------------------------------------------


def test_amzn_gr_keys_preserved():
    """
    build_output_df() must preserve amzn.gr.* keys even though they don't join to SKUs.

    The unjoined row must appear in the output with NaN for asin and sku columns.
    This satisfies the requirement to audit all keys, not just joinable ones.
    """
    fee_df = pd.DataFrame({
        "key_sales_marketplace_sku": [
            "US | US-OHFB-001",
            "US | US-OHFB-002",
            "amzn.gr.ABCD1234",
        ],
        "year": [2026, 2026, 2026],
        "week_num": [1, 1, 1],
        "avg_fee_per_unit": [1.50, 2.00, 3.00],
    })

    sku_df = pd.DataFrame({
        "key_sales_marketplace_sku": ["US | US-OHFB-001", "US | US-OHFB-002"],
        "sku": ["US-OHFB-001", "US-OHFB-002"],
        "asin": ["B0EXAMPLE01", "B0EXAMPLE02"],
        "sales_region": ["US", "US"],
    })

    result = build_output_df(fee_df, sku_df)

    assert len(result) == 3, (
        f"build_output_df must return all 3 rows (including amzn.gr.*), got {len(result)}"
    )

    amzn_row = result[result["key_sales_marketplace_sku"] == "amzn.gr.ABCD1234"]
    assert len(amzn_row) == 1, "amzn.gr.ABCD1234 row must appear in output"
    assert pd.isna(amzn_row["asin"].iloc[0]), (
        "asin must be NaN for unjoined amzn.gr.* keys"
    )
    assert pd.isna(amzn_row["sku"].iloc[0]), (
        "sku must be NaN for unjoined amzn.gr.* keys"
    )


def test_csv_schema_columns():
    """
    build_output_df() must produce all D-11 required columns in the output DataFrame.

    D-11 columns: key_sales_marketplace_sku, country, sales_region, sku, asin,
                  week_start_date, avg_fee_per_unit, currency.
    """
    fee_df = pd.DataFrame({
        "key_sales_marketplace_sku": ["US | US-OHFB-001"],
        "year": [2026],
        "week_num": [1],
        "avg_fee_per_unit": [1.50],
    })

    sku_df = pd.DataFrame({
        "key_sales_marketplace_sku": ["US | US-OHFB-001"],
        "sku": ["US-OHFB-001"],
        "asin": ["B0EXAMPLE01"],
        "sales_region": ["US"],
    })

    result = build_output_df(fee_df, sku_df)

    required_columns = [
        "key_sales_marketplace_sku",
        "country",
        "sales_region",
        "sku",
        "asin",
        "week_start_date",
        "avg_fee_per_unit",
        "currency",
    ]
    for col in required_columns:
        assert col in result.columns, (
            f"D-11 required column '{col}' is missing from build_output_df output"
        )


def test_week_start_is_monday():
    """
    iso_to_week_start() must return the Monday of the given ISO year+week.

    ISO week 1 of 2026 starts on Monday 2025-12-29 (weekday() == 0).
    Year-boundary edge case: ISO week 53 of 2025 must not raise an exception.
    """
    result = iso_to_week_start(2026, 1)

    assert isinstance(result, pd.Timestamp), (
        "iso_to_week_start must return a pd.Timestamp"
    )
    assert result.weekday() == 0, (
        f"iso_to_week_start must return a Monday (weekday 0), got weekday {result.weekday()}"
    )

    # Year-boundary edge case — ISO week 53 exists in 2025 (52+1 weeks)
    try:
        iso_to_week_start(2025, 53)
    except Exception as exc:
        pytest.fail(
            f"iso_to_week_start(2025, 53) must not raise an exception, got: {exc}"
        )


# ---------------------------------------------------------------------------
# DATA-01 / T-04-02: Pydantic schema guard — validate_output_df
# ---------------------------------------------------------------------------


def test_validate_output_df_raises_on_missing_column():
    """
    validate_output_df() must raise pydantic.ValidationError when a required D-11
    column is missing from the output DataFrame.

    Verifies T-04-02 mitigation: Pydantic validation halts execution before CSV
    write when the schema is wrong, preventing silently corrupt output files.

    Test method: build a minimal D-11-compliant DataFrame, drop 'asin', then call
    validate_output_df() — must raise ValidationError (not KeyError or silent pass).
    """
    df = pd.DataFrame({
        "key_sales_marketplace_sku": ["US | US-OHFB-001"],
        "country": ["US"],
        "sales_region": ["US"],
        "sku": ["US-OHFB-001"],
        "asin": ["B0EXAMPLE01"],
        "week_start_date": [datetime.date(2026, 1, 5)],
        "avg_fee_per_unit": [1.50],
        "currency": ["USD"],
    })

    # Drop 'asin' to simulate a missing required D-11 column
    df = df.drop(columns=["asin"])

    with pytest.raises(ValidationError):
        validate_output_df(df)
