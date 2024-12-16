import json
import datetime
import traceback
import time
import random

from os.path import dirname, abspath
from uuid import UUID
from pkgutil import get_data

# =============================================================================

def tick_round(x, factor):
    return factor * round(float(x) / factor, 0)

def vwap_helper( old_qty, old_price, new_qty, new_price, rfact=10 ):
    return round ( ( old_qty*old_price + new_qty*new_price )/( old_qty + new_qty ), rfact )

# =============================================================================

def random_decision( threshold ):
    """ this is a placeholder function to take an action at a random probability """
    return  (random.uniform(0.0, 1.0) <= threshold)

# =============================================================================

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)

class DateTimeDecoder(json.JSONDecoder):
    pass

# =======================================

encoder = DateTimeEncoder()
jsonify = encoder.encode

# =======================================

def http_always_return_json() -> object:
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            # handle different types of errors and return messages accordingly with status code
            except Exception as e:
                print(traceback.format_exc())
                if e.args:
                    emsg = str(e.args[0])
                else:
                    emsg = str(e)
                """
                In order to protect against account information leakage,
                return as little information as possible to the caller.
                if isinstance(e, ValueError):
                    return jsonify({'message': emsg, 'type': 'ValueError'}), 400
                elif isinstance(e, AttributeError):
                    return jsonify({'message': emsg, 'type': 'AttributeError'}), 400
                elif isinstance(e, KeyError):
                    return jsonify({'message': emsg, 'type': 'KeyError'}), 400
                elif isinstance(e, TypeError):
                    return jsonify({'message': emsg, 'type': 'TypeError'}), 400
                else:
                """
                return jsonify({'message': 'Contact Support.', 'type': 'InternalServerError'}), 500
        return wrapped
    return wrapper

# =======================================

def sleep_for(target_seconds, div=2, ulimit=1.1, llimit=0.1):
    """
    Sleeps for a target number of seconds using the monotonic clock,
    splitting the remaining time in half at each sleep interval.

    Args:
    target_seconds: The desired total sleep time in seconds.

    Raises:
    ValueError: If target_seconds is negative.
    """

    if target_seconds < 0:
        raise ValueError("Target sleep time cannot be negative.")

    start_time     = time.monotonic()
    remaining_time = target_seconds
    while remaining_time > llimit:
        time.sleep( min(ulimit,max(remaining_time / div, llimit)) )  # Sleep for half or 0.05 seconds
        remaining_time = target_seconds - (time.monotonic() - start_time)

    # Ensure final sleep completes remaining time, even if slightly above 0.05
    if remaining_time > 0:
        time.sleep(remaining_time)

# =====================================

def save_yml(cfg, filename, mode="w", sort_keys=False, **kwargs):

    if not hasattr(load_yml, "yaml"):
        import yaml
        load_yml.yaml = yaml
        class NoAliasDumper(yaml.Dumper):
            def ignore_aliases(self, data):
                return True
        load_yml.dumper = NoAliasDumper

    with open(filename, mode) as f:
        load_yml.yaml.dump(cfg, stream=f, Dumper=load_yml.dumper, sort_keys=sort_keys, **kwargs)

def load_yml(filename, mode="r", package=None):

    if not hasattr(load_yml, "yaml"):
        import yaml
        load_yml.yaml = yaml
        class NoAliasDumper(yaml.Dumper):
            def ignore_aliases(self, data):
                return True
        load_yml.dumper = NoAliasDumper

    try:
        if package: raise
        with open(filename, mode) as f:
            try:
                return load_yml.yaml.safe_load(f)
            except load_yml.yaml.YAMLError as exc:
                print(exc)
    except:
        try:
            if not package:
                raise Exception("No Package Provided")
            path = filename.split("/")
            cfg = path[-1]
            pkg = ".".join([package] + path[:-1])
            f   = get_data(pkg, cfg).decode("utf-8")
            return load_yml.yaml.safe_load(f)
        except:
            return None

# =========================================================

def Expand(path):
    return dirname(abspath(path))

# =========================================================

if __name__ == "__main__":
    sleep_for( 10.0 )

