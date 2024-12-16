from django.db import migrations


def add_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('post_office', 'EmailTemplate')

    EmailTemplate.objects.create(**{
        "name": "forward",
        "description": "forward",
        "subject": "Upcoming forward settlement",
        "content": "Upcoming Forward Settlement\r\n\r\nThe following forward will settle in 72 hours.\r\n\r\nPlease ensure the target account is correct.\r\n\r\nCash Flow Name: \"{{ name }}\"\r\nAmount (USD): ${{ amount_usd|floatformat:\"2g\" }}\r\nAmount ({{ currency.mnemonic }}): {{ currency.symbol }}{{ amount|floatformat:\"2g\" }}\r\nCurrency: {{ currency.name }} ({{ currency.mnemonic }})\r\nDirection: {{ direction }}\r\nFrequency: {{ payment_type }}\r\nSettlement Date: {{ payment_date }}</td>",
        "html_content": "{% extends \"core/email/layout/base.html\" %}\r\n{% load static %}\r\n{% block content %}\r\n  <p class=\"center\"><img src=\"{% static 'media/email/status/bell.png' %}\"/></p>\r\n  <h2 class=\"pangea-title center\">Upcoming Forward Settlement</h2>\r\n  <p class=\"padded center\">The following forward will settle in 72 hours.</p>\r\n  <p class=\"padded center\">Please ensure the target account is correct.</p>\r\n  <table class=\"full-width table striped\">\r\n    <tr>\r\n      <td>Cash Flow Name:</td>\r\n      <td class=\"content-right\">\"{{ name }}\"</td>\r\n    </tr>\r\n    <tr>\r\n      <td>Amount (USD):</td>\r\n      <td class=\"content-right\">${{ amount_usd|floatformat:\"2g\" }}</td>\r\n    </tr>\r\n    <tr>\r\n      <td>Amount ({{ currency.mnemonic }}):</td>\r\n      <td class=\"content-right\">{{ currency.symbol }}{{ amount|floatformat:\"2g\" }}</td>\r\n    </tr>\r\n    <tr>\r\n      <td>Currency:</td>\r\n      <td class=\"content-right\">{{ currency.name }} ({{ currency.mnemonic }})</td>\r\n    </tr>\r\n    <tr>\r\n      <td>Direction:</td>\r\n      <td class=\"content-right\">{{ direction }}</td>\r\n    </tr>\r\n    <tr>\r\n      <td>Frequency:</td>\r\n      <td class=\"content-right\">{{ payment_type }}</td>\r\n    </tr>\r\n    <tr>\r\n      <td>Settlement Date:</td>\r\n      <td class=\"content-right\">{{ payment_date }}</td>\r\n    </tr>\r\n  </table>\r\n  <p class=\"center\">\r\n    <a class=\"btn bold pangea-dark-button\" href=\"{{ url }}\"\r\n       style=\"display: inline-block !important; padding: 9px; width: auto;\">\r\n      Go To CAsh Flow &rarr;</a>\r\n  </p>\r\n{% endblock %}",
    })
    EmailTemplate.objects.create(**{
        "name": "forward_customer_edit",
        "description": "",
        "subject": "Edit Request Submitted",
        "content": "Edit Request Submitted\r\n\r\n\r\nWe have received your request to edit the cash flow “{{ name }}”. Your Pangea Advisor is \r\nreviewing this request and will reach out to you within 2 business days.\r\n\r\nIf you did not request this edit, please contact us via our support site.\r\n\r\n\r\nThanks,\r\nPangea",
        "html_content": "{% extends \"core/email/layout/base.html\" %}\r\n{% load static %}\r\n{% block content %}  \r\n  <h2 class=\"pangea-title\">Edit Request Submitted</h2>\r\n  <p class=\"pangea-text\">\r\n  We have received your request to edit the cash flow <strong>“{{ name }}”.</strong>\r\n  Your Pangea Advisor is reviewing this request and will reach out to you within 2 business days.\r\n  </p>\r\n  <p class=\"pangea-text\">If you did not request this edit, <a href=\"{{ link_support_url }}\">please contact us via our support site.</a></p>\r\n  <p>&nbsp;</p>\r\n  <p class=\"lightgrey\">Thanks,<br/>Pangea</p>\r\n{% endblock %}",
    })
    EmailTemplate.objects.create(**{
        "name": "ndf_advisor",
        "description": "ndf_advisor",
        "subject": "NDF Order Needs Review",
        "content": "NDF Order Needs Review\r\n\r\n\r\nA customer has booked an NDF:\r\n\r\nCustomer: {{ customer_name }}\r\nCash Flow: {{ cashflow_name }}\r\nHedge ID: {{ cashflow_id }}\r\nForward ID: {{ forward_id }}\r\nPrimary Contact: {{ contact_name }}\r\nPhone: {{ contact_phone }}\r\nEmail: {{ contact_email }}",
        "html_content": "{% extends \"core/email/layout/base.html\" %}\r\n{% load static %}\r\n{% block content %}\r\n  <h2 class=\"pangea-title\">NDF Order Needs Review</h2>\r\n  <p class=\"pangea-text\">A customer has booked an NDF:</p>\r\n  <p class=\"pangea-text\">\r\n    <strong>Customer:</strong> {{ customer_name }}<br/>\r\n    <strong>Cash Flow:</strong> {{ cashflow_name }}<br/>\r\n    <strong>Hedge ID:</strong> {{ cashflow_id }}<br/>\r\n    <strong>Forward ID:</strong> {{ forward_id }}<br/>\r\n    <strong>Primary Contact:</strong> {{ contact_name }}<br/>\r\n    <strong>Phone:</strong> {{ contact_phone }}<br/>\r\n    <strong>Email:</strong> {{ contact_email }}<br/>\r\n  </p>\r\n{% endblock %}",
    })
    EmailTemplate.objects.create(**{
        "name": "forward_customer_drawback",
        "description": "forward_customer_drawback",
        "subject": "Drawback Early Request Submitted",
        "content": "Drawback Early Request Submitted\r\n\r\n\r\nWe have received your request an early drawback for the cash flow “{{ name }}”. \r\nYour Pangea Advisor is reviewing this request and will reach out to you within 2 business days. \r\n\r\nIf you did not request this edit, please contact us via our support site.\r\n\r\n\r\n\r\nThanks,\r\nPangea",
        "html_content": "{% extends \"core/email/layout/base.html\" %}\r\n{% load static %}\r\n{% block content %}  \r\n  <h2 class=\"pangea-title\">Drawback Early Request Submitted</h2>\r\n  <p class=\"pangea-text\">\r\n  We have received your request an early drawback for the cash flow <strong>“{{ name }}”.</strong>\r\n  Your Pangea Advisor is reviewing this request and will reach out to you within 2 business days. \r\n  </p>\r\n  <p class=\"pangea-text\">If you did not request this edit, <a href=\"{{ link_support_url }}\">please contact us via our support site.</a></p>\r\n  <p>&nbsp;</p>\r\n  <p class=\"lightgrey\">Thanks,<br/>Pangea</p>\r\n{% endblock %}",
    })
    EmailTemplate.objects.create(**{
        "name": "forward_advisor_drawback",
        "description": "forward_advisor_drawback",
        "subject": "Drawback Early Request Submitted",
        "content": "Drawback Early Request Submitted\r\n\r\n\r\nA customer has request an early drawback for a cash flow. Review below:\r\n\r\nCustomer: {{ customer_name }}\r\nCash Flow: {{ cashflow_name }}\r\nHedge ID: {{ cashflow_id }}\r\nForward ID: {{ forward_id }}\r\nPrimary Contact: {{ contact_name }}\r\nPhone: {{ contact_phone }}\r\nEmail: {{ contact_email }}",
        "html_content": "{% extends \"core/email/layout/base.html\" %}\r\n{% load static %}\r\n{% block content %}\r\n  <h2 class=\"pangea-title\">Drawback Early Request Submitted</h2>\r\n  <p class=\"pangea-text\">A customer has request an early drawback for a cash flow. Review below:</p>\r\n  <p class=\"pangea-text\">\r\n    <strong>Customer:</strong> {{ customer_name }}<br/>\r\n    <strong>Cash Flow:</strong> {{ cashflow_name }}<br/>\r\n    <strong>Hedge ID:</strong> {{ cashflow_id }}<br/>\r\n    <strong>Forward ID:</strong> {{ forward_id }}<br/>\r\n    <strong>Primary Contact:</strong> {{ contact_name }}<br/>\r\n    <strong>Phone:</strong> {{ contact_phone }}<br/>\r\n    <strong>Email:</strong> {{ contact_email }}<br/>\r\n  </p>\r\n{% endblock %}",
    })
    EmailTemplate.objects.create(**{
        "name": "forward_advisor_edit",
        "description": "forward_advisor_edit",
        "subject": "Edit Request Submitted",
        "content": "Edit Request Submitted\r\n\r\n\r\nA customer has submitted a request to edit a cash flow. Review below:\r\n\r\nCustomer: {{ customer_name }}\r\nCash Flow: {{ cashflow_name }}\r\nHedge ID: {{ cashflow_id }}\r\nForward ID: {{ forward_id }}\r\nPrimary Contact: {{ contact_name }}\r\nPhone: {{ contact_phone }}\r\nEmail: {{ contact_email }}",
        "html_content": "{% extends \"core/email/layout/base.html\" %}\r\n{% load static %}\r\n{% block content %}\r\n  <h2 class=\"pangea-title\">Edit Request Submitted</h2>\r\n  <p class=\"pangea-text\">A customer has submitted a request to edit a cash flow. Review below:</p>\r\n  <p class=\"pangea-text\">\r\n    <strong>Customer:</strong> {{ customer_name }}<br/>\r\n    <strong>Cash Flow:</strong> {{ cashflow_name }}<br/>\r\n    <strong>Hedge ID:</strong> {{ cashflow_id }}<br/>\r\n    <strong>Forward ID:</strong> {{ forward_id }}<br/>\r\n    <strong>Primary Contact:</strong> {{ contact_name }}<br/>\r\n    <strong>Phone:</strong> {{ contact_phone }}<br/>\r\n    <strong>Email:</strong> {{ contact_email }}<br/>\r\n  </p>\r\n{% endblock %}",
    })
    EmailTemplate.objects.create(**{
        "name": "credit_deposit_customer",
        "description": "credit_deposit_customer",
        "subject": "Credit Deposit Request Received",
        "content": "Credit Deposit Request Received\r\n\r\n\r\nYour advisor will contact you for the quickest and most secure way to \r\ndeposit funds into your Auto-Pilot credit account.\r\n\r\nWe have received your request for a credit deposit. Your Pangea Advisor is \r\nreviewing this request and will reach out to you within 2 business days to \r\nassist you in a secure and fast deposit.\r\n\r\n\r\nThanks,\r\nPangea",
        "html_content": "{% extends \"core/email/layout/base.html\" %}\r\n{% load static %}\r\n{% block content %}  \r\n  <h2 class=\"pangea-title\">Credit Deposit Request Received</h2>\r\n  <p class=\"pangea-text\">\r\n  Your advisor will contact you for the quickest and most secure way to deposit funds into your Auto-Pilot credit account.\r\n  </p>\r\n  <p class=\"pangea-text\">\r\n  We have received your request for a credit deposit. Your Pangea Advisor is \r\n  reviewing this request and will reach out to you within 2 business days to \r\n  assist you in a secure and fast deposit.\r\n  </p>\r\n  <p>&nbsp;</p>\r\n  <p class=\"lightgrey\">Thanks,<br/>Pangea</p>\r\n{% endblock %}",
    })
    EmailTemplate.objects.create(**{
        "name": "credit_deposit_advisor",
        "description": "credit_deposit_advisor",
        "subject": "Credit Deposit Request Submitted",
        "content": "Credit Deposit Request Submitted\r\n\r\n\r\nA customer has request credit deposit assistance. Review below:\r\n\r\nCustomer: {{ customer_name }}\r\nPrimary Contact: {{ contact_name }}\r\nPhone: {{ contact_phone }}\r\nEmail: {{ contact_email }}",
        "html_content": "{% extends \"core/email/layout/base.html\" %}\r\n{% load static %}\r\n{% block content %}\r\n  <h2 class=\"pangea-title\">Credit Deposit Request Submitted</h2>\r\n  <p class=\"pangea-text\">A customer has request credit deposit assistance. Review below:</p>\r\n  <p class=\"pangea-text\">\r\n    <strong>Customer:</strong> {{ customer_name }}<br/>\r\n    <strong>Primary Contact:</strong> {{ contact_name }}<br/>\r\n    <strong>Phone:</strong> {{ contact_phone }}<br/>\r\n    <strong>Email:</strong> {{ contact_email }}<br/>\r\n  </p>\r\n{% endblock %}",
    })


class Migration(migrations.Migration):
    dependencies = [
        ('notification', '0001_initial'),
        ('post_office', '0011_models_help_text'),
    ]

    operations = [
        migrations.RunPython(add_templates)
    ]
