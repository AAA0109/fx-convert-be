import csv
import requests
from django.db import migrations

def populate_currency_unit(apps, schema_editor):
    Currency = apps.get_model('currency', 'Currency')  # Get the Currency model dynamically

    # URL of the CSV file
    csv_url = "https://raw.githubusercontent.com/datasets/currency-codes/master/data/codes-all.csv"

    # Fetch the CSV data from the URL
    response = requests.get(csv_url)
    if response.status_code == 200:
        # Read the CSV data from the response content
        csv_reader = csv.DictReader(response.text.splitlines())

        saved_currencies = []

        # Iterate through each row in the CSV
        for row in csv_reader:
            # Get the currency mnemonic and minor unit from the CSV row
            mnemonic = row['AlphabeticCode']
            minor_unit = row['MinorUnit']
            numeric_code = row['NumericCode']
            if mnemonic in saved_currencies:
                continue
            try:
                # Check if the currency exists in the database
                currency = Currency.objects.get(mnemonic=mnemonic)
                if currency is not None and minor_unit != '':
                    # Update the Unit column in the Currency object
                    currency.unit = minor_unit
                    currency.numeric_code = numeric_code

                    # Save the changes to the Currency object
                    currency.save()
                    saved_currencies.append(mnemonic)
            except Currency.DoesNotExist:
                continue
    else:
        print(f"Error fetching CSV: {response.status_code}")

class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0022_alter_deliverytime_country'),
    ]

    operations = [
        migrations.RunPython(populate_currency_unit),
    ]
