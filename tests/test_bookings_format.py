"""Tests for checkout formatting rules in bookings_format.py."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from airbnb_calendar.bookings_format import (
    WARNING_ICON,
    _format_checkout_line,
    _listing_label,
    _next_checkin_for_listing,
    format_checkouts_text,
    print_checkouts_diff,
    print_checkouts_diff_from_payload,
    write_checkouts_text,
)

EB = "Loft c/ Varanda Solarenga a 5 Minutos Ponte Luíz I"
EA = "Espaço Renovado a 5 minutos a pé da Ponte Luíz I"
T0 = "Estúdio Renovado c/ metro à porta"
T1 = "T1 Renovado c/ metro à porta"
T2 = "Totalmente Renovado, metro à porta"


def _booking(
    listing_name: str,
    start_date: str,
    end_date: str,
    *,
    confirmation_code: str = "HMTEST001",
) -> dict:
    return {
        "confirmationCode": confirmation_code,
        "listingName": listing_name,
        "startDate": start_date,
        "endDate": end_date,
    }


def _payload(*bookings: dict) -> dict:
    return {"bookings": list(bookings)}


class TestListingLabels:
    @pytest.mark.parametrize(
        ("listing_name", "label"),
        [
            (T0, "T0"),
            (T1, "T1"),
            (T2, "T2"),
            (EA, "EA"),
            (EB, "EB"),
        ],
    )
    def test_known_listing_maps_to_label(self, listing_name: str, label: str) -> None:
        assert _listing_label(listing_name) == label

    def test_unknown_listing_returns_none(self) -> None:
        assert _listing_label("Cleaning") is None
        assert _listing_label(None) is None


class TestNextCheckinForListing:
    def test_returns_earliest_future_checkin_for_same_listing(self) -> None:
        bookings = [
            _booking(EB, "2026-06-27", "2026-07-01", confirmation_code="A"),
            _booking(EB, "2026-07-03", "2026-07-07", confirmation_code="B"),
        ]
        nxt = _next_checkin_for_listing(bookings, EB, date(2026, 6, 20))
        assert nxt is not None
        assert nxt["confirmationCode"] == "A"

    def test_ignores_other_listings(self) -> None:
        bookings = [_booking(T0, "2026-06-21", "2026-06-30")]
        assert _next_checkin_for_listing(bookings, EB, date(2026, 6, 20)) is None


class TestWarningIconRule:
    """⚠️ when the same listing has a check-in the day after checkout."""

    def test_adds_warning_on_same_listing_next_day_turnover(self) -> None:
        bookings = [
            _booking(EB, "2026-06-04", "2026-06-08"),
            _booking(EB, "2026-06-09", "2026-06-14"),
        ]
        line = _format_checkout_line(date(2026, 6, 8), "EB", bookings, EB)
        assert line == f"8 seg. EB {WARNING_ICON}"

    def test_no_warning_when_next_same_listing_checkin_is_later(self) -> None:
        bookings = [
            _booking(EB, "2026-06-17", "2026-06-20"),
            _booking(EB, "2026-06-27", "2026-07-01"),
        ]
        line = _format_checkout_line(date(2026, 6, 20), "EB", bookings, EB)
        assert WARNING_ICON not in line
        assert line == "20 sáb. a ? EB"

    def test_no_warning_when_only_other_listing_checks_in_next_day(self) -> None:
        bookings = [
            _booking(EB, "2026-06-17", "2026-06-20"),
            _booking(T0, "2026-06-21", "2026-06-30"),
            _booking(EB, "2026-06-27", "2026-07-01"),
        ]
        line = _format_checkout_line(date(2026, 6, 20), "EB", bookings, EB)
        assert WARNING_ICON not in line


class TestNextCheckinMarkerRule:
    """a {day} when gap is 4-6 days; a ? when gap is at least one week."""

    def test_adds_day_marker_when_gap_is_between_four_and_six_days(self) -> None:
        bookings = [
            _booking(T1, "2026-06-05", "2026-06-11"),
            _booking(T1, "2026-06-16", "2026-06-20"),
        ]
        line = _format_checkout_line(date(2026, 6, 11), "T1", bookings, T1)
        assert line == "11 qui. a 16 T1"

    def test_adds_question_mark_when_gap_is_at_least_one_week(self) -> None:
        bookings = [
            _booking(EB, "2026-06-17", "2026-06-20"),
            _booking(EB, "2026-06-27", "2026-07-01"),
        ]
        line = _format_checkout_line(date(2026, 6, 20), "EB", bookings, EB)
        assert line == "20 sáb. a ? EB"

    def test_no_day_marker_when_gap_is_exactly_three_days(self) -> None:
        bookings = [
            _booking(T1, "2026-06-05", "2026-06-11"),
            _booking(T1, "2026-06-14", "2026-06-20"),
        ]
        line = _format_checkout_line(date(2026, 6, 11), "T1", bookings, T1)
        assert line == "11 qui. T1"

    def test_no_day_marker_when_gap_is_three_days_or_less(self) -> None:
        bookings = [
            _booking(EA, "2026-06-05", "2026-06-08"),
            _booking(EA, "2026-06-10", "2026-06-14"),
        ]
        line = _format_checkout_line(date(2026, 6, 8), "EA", bookings, EA)
        assert " a " not in line
        assert line == "8 seg. EA"

    def test_no_marker_when_no_future_same_listing_checkin(self) -> None:
        bookings = [_booking(T0, "2026-06-21", "2026-06-30")]
        line = _format_checkout_line(date(2026, 6, 30), "T0", bookings, T0)
        assert line == "30 ter. T0"


class TestFormatCheckoutsText:
    def test_outputs_month_header_and_weekday(self) -> None:
        text = format_checkouts_text(_payload(_booking(T2, "2026-06-10", "2026-06-14")))
        assert text.splitlines() == ["JUN.", "14 dom. T2"]

    def test_sorts_same_day_by_label_order(self) -> None:
        text = format_checkouts_text(
            _payload(
                _booking(EB, "2026-06-09", "2026-06-14", confirmation_code="EB1"),
                _booking(EA, "2026-06-10", "2026-06-14", confirmation_code="EA1"),
                _booking(T2, "2026-06-10", "2026-06-14", confirmation_code="T21"),
            )
        )
        lines = text.splitlines()
        assert lines[0] == "JUN."
        labels = [line.rsplit(" ", 1)[-1] for line in lines[1:]]
        assert labels == ["T2", "EA", "EB"]

    def test_skips_unknown_listings(self) -> None:
        text = format_checkouts_text(
            _payload(_booking("Cleaning", "2026-06-01", "2026-06-05"))
        )
        assert text == ""

    def test_adds_new_month_header_when_month_changes(self) -> None:
        text = format_checkouts_text(
            _payload(
                _booking(T2, "2026-06-10", "2026-06-14"),
                _booking(T2, "2026-07-04", "2026-07-11"),
            )
        )
        assert text.splitlines()[:3] == ["JUN.", "14 dom. a ? T2", "JUL."]

    def test_realistic_june_scenario_matches_documented_rules(self) -> None:
        text = format_checkouts_text(
            _payload(
                _booking(EA, "2026-06-05", "2026-06-08"),
                _booking(EA, "2026-06-10", "2026-06-14"),
                _booking(EB, "2026-06-04", "2026-06-08"),
                _booking(EB, "2026-06-09", "2026-06-14"),
                _booking(T2, "2026-06-06", "2026-06-09"),
                _booking(T2, "2026-06-10", "2026-06-14"),
                _booking(T1, "2026-06-05", "2026-06-11"),
                _booking(T1, "2026-06-16", "2026-06-20"),
                _booking(T2, "2026-06-16", "2026-06-20", confirmation_code="T22"),
                _booking(EA, "2026-06-16", "2026-06-20", confirmation_code="EA2"),
                _booking(EB, "2026-06-16", "2026-06-20", confirmation_code="EB2"),
            )
        )
        lines = text.splitlines()
        assert "8 seg. EA" in lines
        assert f"8 seg. EB {WARNING_ICON}" in lines
        assert f"9 ter. T2 {WARNING_ICON}" in lines
        assert "11 qui. a 16 T1" in lines
        assert "14 dom. T2" in lines
        assert "14 dom. EA" in lines
        assert "14 dom. EB" in lines


class TestWriteCheckoutsText:
    def test_writes_file_and_prints_summary_to_stdout(
        self, tmp_path: Path, capsys
    ) -> None:
        root = tmp_path
        bookings_path = root / "bookings.json"
        bookings_path.write_text(
            json.dumps(_payload(_booking(T2, "2026-06-10", "2026-06-14"))),
            encoding="utf-8",
        )
        out_path = write_checkouts_text(bookings_path=bookings_path, root=root)
        captured = capsys.readouterr()
        assert out_path.read_text(encoding="utf-8") == captured.out
        assert "Wrote checkout summary" in captured.err


class TestPrintCheckoutsDiff:
    def test_returns_false_when_text_is_identical(self, tmp_path: Path) -> None:
        existing = tmp_path / "bookings.txt"
        existing.write_text("JUN.\n8 seg. EB\n", encoding="utf-8")
        assert print_checkouts_diff("JUN.\n8 seg. EB\n", existing_path=existing) is False

    def test_prints_removed_and_added_rows(self, tmp_path: Path, capsys) -> None:
        existing = tmp_path / "bookings.txt"
        existing.write_text("JUN.\n8 seg. EB\n", encoding="utf-8")
        changed = print_checkouts_diff(
            "JUN.\n8 seg. EB ⚠️\n",
            existing_path=existing,
        )
        output = capsys.readouterr().out
        assert changed is True
        assert output.splitlines() == ["- 8 seg. EB", f"+ 8 seg. EB {WARNING_ICON}"]

    def test_diff_from_payload_uses_formatted_output(self, tmp_path: Path, capsys) -> None:
        existing = tmp_path / "bookings.txt"
        existing.write_text("JUN.\n8 seg. EB\n", encoding="utf-8")
        payload = _payload(
            _booking(EA, "2026-06-05", "2026-06-08"),
            _booking(EA, "2026-06-10", "2026-06-14"),
        )
        changed = print_checkouts_diff_from_payload(payload, existing_path=existing)
        output = capsys.readouterr().out.splitlines()
        assert changed is True
        assert "- 8 seg. EB" in output
        assert "+ 8 seg. EA" in output
        assert "+ 14 dom. EA" in output
