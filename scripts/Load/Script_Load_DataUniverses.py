"""
Script that loads all the data from local data universes, stored in files, into the database.
"""

import os
import sys

from hdlib.Universe.Historical.HistUniverseProvider_Files import HistUniverseProvider_Files
from scripts.lib.only_local import only_allow_local


def run(data_config_path: str):
    from loaders.load_universe import load_all_universes

    u_provider = HistUniverseProvider_Files(config_path=data_config_path)
    print("Loading all universes")
    load_all_universes(u_provider)
    print("Done loading all universes")


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    data_config_path = '/Users/nathaniel/Pangea/data/ProxyWorld/config.toml'
    # data_config_path = r"C:\Users\jkirk\OneDrive\code\hedgedesk_ml\src\DataStore\ProxyWorld/config.toml"

    run(data_config_path)
