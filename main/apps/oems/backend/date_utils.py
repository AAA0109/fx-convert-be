from datetime import datetime, timedelta, date

# =============================================================================

GBL_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
ALT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

def now(utc=True):
    return datetime.utcnow() if utc else datetime.now()

def check_after( date, strict=False ):
    return (now() >= date) if strict else (now() > date)

def add_time( date, **kwargs ):
    return date + timedelta(**kwargs)

def parse_datetime( date_string: str, fmt=GBL_DATE_FORMAT, alt_fmt=ALT_DATE_FORMAT ):
    if isinstance( date_string, datetime ):
        return date_string
    try:
        ret = datetime.fromisoformat(date_string)
        return ret.replace(tzinfo=None)
    except:
        try:
            return datetime.strptime(date_string, fmt)
        except:
            try:
                return datetime.strptime(date_string, alt_fmt)
            except:
                return datetime.strptime(date_string, "%Y-%m-%d")
            
def parse_date( date_string, fmt='%Y-%m-%d' ):
    if isinstance( date_string, (datetime, date) ):
        return date_string
    return datetime.strptime(date_string, fmt).date()

def sec_diff( new_dt, old_dt ):
    return (new_dt-old_dt).total_seconds()

# =============================================================================

