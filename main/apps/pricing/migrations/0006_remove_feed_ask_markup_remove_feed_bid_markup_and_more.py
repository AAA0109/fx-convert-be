# Generated by Django 4.2.11 on 2024-04-22 08:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0005_rename_type_feed_feed_feed_type"),
    ]

    operations = [
        migrations.RemoveField(model_name="feed", name="ask_markup",),
        migrations.RemoveField(model_name="feed", name="bid_markup",),
        migrations.RemoveField(model_name="feed", name="fwd_point_src",),
        migrations.RemoveField(model_name="feed", name="quote_type",),
        migrations.RemoveField(model_name="feed", name="value_date",),
    ]
