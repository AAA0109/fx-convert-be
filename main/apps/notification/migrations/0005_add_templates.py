from django.db import migrations


def add_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('post_office', 'EmailTemplate')
    instance = EmailTemplate.objects.get(name='company_non_sellable_forward')
    instance.content = """
Hi {{company_rep}},

Rate Request for {{company_name}}:
{% for item in items %}
Buy Currency: {{ item.currency_from.mnemonic }}
Sell Currency: {{ item.currency_to.mnemonic }}
Spot rate: {{ item.rate }}
Amount: {{ item.amount_to|floatformat:"2g" }}
Maturity Date: {{ item.date }}
{% endfor %}
        """
    instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('notification', '0004_add_templates'),
    ]

    operations = [
        migrations.RunPython(add_templates),
    ]
