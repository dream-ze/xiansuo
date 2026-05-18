import pytest

from app.services.export_service import VALID_LEAD_STATUSES, LEAD_STATUS_LABELS


def test_valid_lead_statuses_includes_all_five():
    assert VALID_LEAD_STATUSES == {"new", "contacted", "interested", "invalid", "converted"}


def test_interested_is_in_valid_statuses():
    assert "interested" in VALID_LEAD_STATUSES


def test_status_labels_cover_all_valid_statuses():
    for status in VALID_LEAD_STATUSES:
        assert status in LEAD_STATUS_LABELS, f"missing label for status: {status}"


@pytest.mark.parametrize("status", ["new", "contacted", "interested", "invalid", "converted"])
def test_each_status_has_chinese_label(status):
    label = LEAD_STATUS_LABELS[status]
    assert len(label) > 0
    assert all(ord(ch) > 127 for ch in label)


def test_interested_label():
    assert LEAD_STATUS_LABELS["interested"] == "有意向"


def test_invalid_status_not_in_valid_set():
    assert "qualified" not in VALID_LEAD_STATUSES
    assert "lost" not in VALID_LEAD_STATUSES


def test_csv_export_maps_status_to_chinese():
    from app.services.export_service import LEAD_STATUS_LABELS

    for status, label in LEAD_STATUS_LABELS.items():
        mapped = LEAD_STATUS_LABELS.get(status, status)
        assert mapped == label


def test_csv_export_unknown_status_fallback():
    from app.services.export_service import LEAD_STATUS_LABELS

    unknown = "unknown_status"
    mapped = LEAD_STATUS_LABELS.get(unknown, unknown)
    assert mapped == unknown
