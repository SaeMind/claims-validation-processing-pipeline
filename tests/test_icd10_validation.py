from src.icd10_validator import is_valid_icd10


def test_valid_icd10() -> None:
    assert is_valid_icd10("I10") is True
    assert is_valid_icd10("M17.11") is True


def test_invalid_icd10() -> None:
    assert is_valid_icd10("123") is False
