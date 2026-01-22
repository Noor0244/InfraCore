from datetime import datetime
import pytz
from jinja2 import pass_context

# Usage: {{ utc_dt|local_dt('Asia/Kolkata') }}
def local_dt(dt, tz_name='Asia/Kolkata', fmt='%d/%m/%Y %H:%M:%S'):
    if not dt:
        return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    local = dt.astimezone(pytz.timezone(tz_name))
    return local.strftime(fmt)
