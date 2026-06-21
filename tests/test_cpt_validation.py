from src.cpt_validator import is_valid_modifier, is_valid_procedure_code


def test_cpt_and_hcpcs_codes() -> None:
    assert is_valid_procedure_code("99213") is True
    assert is_valid_procedure_code("G0438") is True
    assert is_valid_procedure_code("BAD") is False


def test_modifier_validation() -> None:
    assert is_valid_modifier("25") is True
    assert is_valid_modifier("LT") is True
    assert is_valid_modifier("LONG") is False
