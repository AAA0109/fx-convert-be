from django.db import migrations


def update_template(apps, *_):
    EmailTemplate = apps.get_model('post_office', 'EmailTemplate')
    instance = EmailTemplate.objects.get(name='trade_confirmation_pdf')
    instance.html_content = """{% extends "core/email/layout/trade_confirmation.html" %}
{% load static %}
{% block cover %}
    <b class="orange">{{company}}</b>

    <h1>{{title}}</h1>
    <dl>
        <dd>{{operation}}</dd>
        <dd>{{date}}</dd>
        <dd></dd>
        <dd class="opacity-50">Order ID: {{order_id}}</dd>
    </dl>
    <i></i>
{% endblock %}

{% block page-header %}
    <h2>EXECUTION DETAILS</h2>
    &nbsp;
    &nbsp;
    &nbsp;
    <span>{{sub_title}}</span>
    <span class="opacity-50 float-right">{{company}}&nbsp;&nbsp;{{date}}&nbsp;&nbsp;Order ID: {{order_id}}</span>
{% endblock %}

{% block page-content %}
    <h2>Order:</h2>
    {{table_content|safe}}
{% endblock %}

{% block disclaimer-content %}

  {% if disclaimer %}
    {{ disclaimer|safe }}
  {% else %}
    <p>The indicative revaluation information ("Values") contained in this document are confidential and are provided as part of the account statement by Pangea Technologies Inc. The Values provided use the prevailing market rates, and will alter with changing market conditions. The provision of a Value does not constitute an offer or bid to unwind the transaction. This is not a confirmation or settlement statement. Confirmations and settlement statements are issued directly to you by Pangea Technologies Inc. at the time of the transaction, and are always to be considered the governing documents for these transactions. Subject to applicable laws and regulations, Pangea Technologies Inc. accepts no responsibility for any loss or damage resulting from any error or negligent act or otherwise in relation to the information provided. If you are not the intended recipient, please do not disseminate, copy or use this information. If you have received this document in error, please immediately contact us at <a href="mailto:support@pangea.io">support@pangea.io</a></p>
  {% endif %}

{% endblock %}

{% block disclaimer-footer %}
    Pangea © 2024 All Rights Reserved
{% endblock %}"""

    instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('notification', '0006_add_templates'),
    ]

    operations = [
        migrations.RunPython(update_template),
    ]
