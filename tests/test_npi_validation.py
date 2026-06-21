from src.npi_validator import validate_npi_checksum


def test_valid_npi_checksum() -> None:
    assert validate_npi_checksum("1234567893") is True


def test_invalid_npi_checksum() -> None:
    assert validate_npi_checksum("1234567890") is False
