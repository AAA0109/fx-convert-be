#! /bin/bash

############################
# Load the data
############################
python manage.py loaddata main/apps/currency/fixtures/currencies.json
python manage.py loaddata main/apps/currency/fixtures/fxpairs.json
python manage.py loaddata main/apps/currency/fixtures/fxpairs.json
python manage.py loaddata main/apps/currency/fixtures/fxpairs.json
python manage.py loaddata main/apps/dataprovider/fixtures/dataprovider.json
python manage.py loaddata main/apps/marketdata/fixtures/fxestimators.json
python manage.py loaddata main/apps/marketdata/fixtures/ircurves.json
