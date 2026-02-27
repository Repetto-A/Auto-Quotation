from datetime import timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def get_arg_tz():
    """
    Return Argentina timezone if IANA tz database is available.
    Fallback to fixed UTC-3 so the app keeps working on Windows environments
    where tzdata is not installed.
    """
    try:
        return ZoneInfo("America/Argentina/Buenos_Aires")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=-3))
