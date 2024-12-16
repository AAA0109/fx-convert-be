from django.db import migrations


def add_templates(apps, *_):
    EmailTemplate = apps.get_model('post_office', 'EmailTemplate')
    template_items = [
        {
            "name": "trade_confirmation_pdf",
            "description": "",
            "subject": "TradeConfirmation.pdf",
            "content": "",
            "html_content": "{% extends \"core/email/layout/trade_confirmation.html\" %}\r\n{% load static %}\r\n{% block cover %}\r\n    <b class=\"orange\">{{company}}</b>\r\n\r\n    <h1>{{title}}</h1>\r\n    <dl>\r\n        <dd>{{operation}}</dd>\r\n        <dd>{{date}}</dd>\r\n        <dd></dd>\r\n        <dd class=\"opacity-50\">Order ID: {{order_id}}</dd>\r\n    </dl>\r\n    <i></i>\r\n{% endblock %}\r\n\r\n{% block page-header %}\r\n    <h2>EXECUTION DETAILS</h2>\r\n    &nbsp;\r\n    &nbsp;\r\n    &nbsp;\r\n    <span>{{sub_title}}</span>\r\n    <span class=\"opacity-50 float-right\">{{company}}&nbsp;&nbsp;{{date}}&nbsp;&nbsp;Order ID: {{order_id}}</span>\r\n{% endblock %}\r\n\r\n{% block page-content %}\r\n    <h2>Order:</h2>\r\n    {{table_content|safe}}\r\n{% endblock %}\r\n\r\n{% block disclaimer-content %}\r\n<p>Lorem ipsum dolor sit amet consectetur adipiscing elit Ut et massa mi. Aliquam in hendrerit urna. Pellentesque sit amet sapien fringilla, mattis ligula consectetur,\r\nultrices mauris. Maecenas vitae mattis tellus. Nullam quis imperdiet augue. Vestibulum auctor ornare leo, non suscipit magna interdum eu. Curabitur pellentesque\r\nnibh nibh, at maximus ante fermentum sit amet. Pellentesque commodo lacus at sodales sodales. Quisque sagittis orci ut diam condimentum, vel euismod erat\r\nplacerat. In iaculis arcu eros, eget tempus orci facilisis id. Praesent lorem orci, mattis non efficitur id, ultricies vel nibh. Sed volutpat lacus vitae gravida viverra. Fusce\r\nvel tempor elit. Proin tempus, magna id scelerisque vestibulum, nulla ex pharetra sapien, tempor posuere massa neque nec felis. Aliquam sem ipsum, vehicula ac\r\ntortor vel, egestas ullamcorper dui. Curabitur at risus sodales, tristique est id, euismod justo. Mauris nec leo non libero sodales lobortis. Quisque a neque pretium,\r\ndictum tellus vitae, euismod neque. Nulla facilisi. Phasellus ultricies dignissim nibh ut cursus. Nam et quam sit amet turpis finibus maximus tempor eget augue.\r\nAenean at ultricies lorem. Sed egestas ligula tortor, sit amet mattis ex feugiat non. Duis purus diam, dictum et ante at, commodo iaculis urna. Aenean lacinia, nisl id\r\nvehicula condimentum, enim massa.</p>\r\n\r\n<p>Lorem ipsum dolor sit amet consectetur adipiscing elit Ut et massa mi. Aliquam in hendrerit urna. Pellentesque sit amet sapien fringilla, mattis ligula consectetur,\r\nultrices mauris. Maecenas vitae mattis tellus. Nullam quis imperdiet augue. Vestibulum auctor ornare leo, non suscipit magna interdum eu. Curabitur pellentesque\r\nnibh nibh, at maximus ante fermentum sit amet. Pellentesque commodo lacus at sodales sodales. Quisque sagittis orci ut diam condimentum, vel euismod erat\r\nplacerat. In iaculis arcu eros, eget tempus orci facilisis id. Praesent lorem orci, mattis non efficitur id, ultricies vel nibh. Sed volutpat lacus vitae gravida viverra. Fusce\r\nvel tempor elit. Proin tempus, magna id scelerisque vestibulum, nulla ex pharetra sapien, tempor posuere massa neque nec felis. Aliquam sem ipsum, vehicula ac\r\ntortor vel, egestas ullamcorper dui. Curabitur at risus sodales, tristique est id, euismod justo. Mauris nec leo non libero sodales lobortis. Quisque a neque pretium,\r\ndictum tellus vitae, euismod neque. Nulla facilisi. Phasellus ultricies dignissim nibh ut cursus. Nam et quam sit amet turpis finibus maximus tempor eget augue.\r\nAenean at ultricies lorem. Sed egestas ligula tortor, sit amet mattis ex feugiat non. Duis purus diam, dictum et ante at, commodo iaculis urna. Aenean lacinia, nisl id\r\nvehicula condimentum, enim massa.</p>\r\n\r\n{% endblock %}\r\n\r\n{% block disclaimer-footer %}\r\n    Pangea © 2024 All Rights Reserved\r\n{% endblock %}",
        },
        {
            "name": "trade_confirmation",
            "description": "",
            "subject": "Confirmation for Order: {{order_id}}",
            "content": "",
            "html_content": "This confirmation is sent to you in regards to Order: {{order_id}} booked by {{company}} for settlement on {{date}}.",
        },
        {
            "name": "mark_to_market",
            "description": "",
            "subject": "Mark to Market Statement - {{date}}",
            "content": "",
            "html_content": "<p>Please find your current mark to market report attached.</p>\r\n<p>These summaries are designed to value positions based upon the prices available in the current market.</p>\r\n<p>The report lists your transactions and margin deposits, along with the prevailing market valuations.</p>",
        }
    ]
    for template in template_items:
        EmailTemplate.objects.create(**template)


class Migration(migrations.Migration):
    dependencies = [
        ('notification', '0005_add_templates'),
    ]

    operations = [
        migrations.RunPython(add_templates),
    ]
