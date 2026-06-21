"""ICD-10-CM diagnosis validation utilities."""

import re

ICD10_PATTERN = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$")


def normalize_icd10(code: str) -> str:
    """
    Normalize an ICD-10-CM code by uppercasing and trimming whitespace.

    Parameters:
        code: Raw diagnosis code.

    Returns:
        Normalized diagnosis code.
    """
    return code.strip().upper()


def is_valid_icd10(code: str) -> bool:
    """
    Validate ICD-10-CM code syntax.

    Parameters:
        code: Candidate diagnosis code.

    Returns:
        True when code syntax resembles ICD-10-CM; otherwise False.
    """
    return bool(ICD10_PATTERN.match(normalize_icd10(code)))
