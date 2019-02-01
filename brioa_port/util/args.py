
def parse_period_arg(arg: str) -> int:
    """
    Makes sure that a period argument is a valid postive integer.
    """
    try:
        period = int(arg)
    except ValueError:
        raise ValueError("Period must be an integer")
    if period < 0:
        raise ValueError("Period cannot be negative")
    return period
