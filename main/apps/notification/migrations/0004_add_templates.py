from django.db import migrations


def add_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('post_office', 'EmailTemplate')
    EmailTemplate.objects.create(**{
        "name": "company_non_sellable_forward",
        "description": "company_non_sellable_forward",
        "subject": "New Non-sellable forward",
        "content": """
Hi {{company_rep}},

Rate Request for {{company_name}}:
Buy Currency: {{ currency_from.mnemonic }}
Sell Currency: {{ currency_to.mnemonic }}
Spot rate: {{ rate }}
Amount: {{ amount_to|floatformat:"2g" }}
Maturity Date: {{ date }}
        """,
        "html_content": "",
    })


def create_frontend_auto_login(apps, schema_editor):
    Config = apps.get_model('core', 'Config')
    Config.objects.update_or_create(
        defaults={
            'value': 'teste@teste.com,teste2@teste.com'
        },
        path='corpay/order/email_recipients',
    )


class Migration(migrations.Migration):
    dependencies = [
        ('notification', '0003_add_templates'),
    ]

    operations = [
        migrations.RunPython(add_templates),
        migrations.RunPython(create_frontend_auto_login),
    ]
