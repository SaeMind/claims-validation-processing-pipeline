"""NPI validation utilities."""


def validate_npi_checksum(npi: str) -> bool:
    """
    Validate a 10-digit National Provider Identifier using the CMS Luhn variant.

    Parameters:
        npi: Candidate NPI string.

    Returns:
        True when the NPI has a valid format and check digit; otherwise False.
    """
    if len(npi) != 10 or not npi.isdigit():
        return False

    payload = "80840" + npi[:-1]
    total = 0
    double = True
    for char in reversed(payload):
        value = int(char)
        if double:
            value *= 2
            if value > 9:
                value -= 9
        total += value
        double = not double
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(npi[-1])
