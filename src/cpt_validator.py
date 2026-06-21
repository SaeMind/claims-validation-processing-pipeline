"""CPT and HCPCS procedure validation utilities."""

import re

CPT_PATTERN = re.compile(r"^\d{5}$")
HCPCS_PATTERN = re.compile(r"^[A-Z]\d{4}$")
MODIFIER_PATTERN = re.compile(r"^[A-Z0-9]{2}$")


def normalize_procedure_code(code: str) -> str:
    """
    Normalize a CPT or HCPCS code.

    Parameters:
        code: Raw procedure code.

    Returns:
        Uppercased stripped code.
    """
    return code.strip().upper()


def is_valid_procedure_code(code: str) -> bool:
    """
    Validate CPT or HCPCS syntax.

    Parameters:
        code: Candidate procedure code.

    Returns:
        True for valid CPT or HCPCS syntax; otherwise False.
    """
    normalized = normalize_procedure_code(code)
    return bool(CPT_PATTERN.match(normalized) or HCPCS_PATTERN.match(normalized))


def is_valid_modifier(modifier: str | None) -> bool:
    """
    Validate procedure modifier syntax.

    Parameters:
        modifier: Optional two-character modifier.

    Returns:
        True when modifier is absent or syntactically valid.
    """
    if modifier is None or modifier == "":
        return True
    return bool(MODIFIER_PATTERN.match(modifier.strip().upper()))
