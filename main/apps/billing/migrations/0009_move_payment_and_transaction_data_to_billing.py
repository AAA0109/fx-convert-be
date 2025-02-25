# Generated by Django 4.2.10 on 2024-03-26 04:56

from django.db import migrations

def get_payment_migrate_data_sql() -> str:
    return """
        INSERT INTO billing_payment (
            id,
            created,
            modified,
            amount,
            method,
            payment_type,
            payment_status
        )
        SELECT
            id,
            created,
            modified,
            amount,
            method,
            payment_type,
            payment_status
        FROM
            payment_payment;
        SELECT setval(pg_get_serial_sequence('"billing_payment"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "billing_payment";
    """

def get_reverse_payment_migrate_data_sql() -> str:
    return """
            INSERT INTO payment_payment (
                id,
                created,
                modified,
                amount,
                method,
                payment_type,
                payment_status
            )
            SELECT
                id,
                created,
                modified,
                amount,
                method,
                payment_type,
                payment_status
            FROM
                billing_payment;
        """

def get_transaction_migrate_data_sql() -> str:
    return """
        INSERT INTO billing_transaction (
            id,
            created,
            modified,
            txn_id,
            payment_id
        )
        SELECT
            id,
            created,
            modified,
            txn_id,
            payment_id
        FROM
            payment_transaction;
        SELECT setval(pg_get_serial_sequence('"billing_transaction"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "billing_transaction";
    """

def get_reverse_transaction_migrate_data_sql() -> str:
    return """
            INSERT INTO payment_transaction (
                id,
                created,
                modified,
                txn_id,
                payment_id
            )
            SELECT
                id,
                created,
                modified,
                txn_id,
                payment_id
            FROM
                billing_transaction;
        """


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0008_payment_transaction'),
    ]

    operations = [
        migrations.RunSQL(get_payment_migrate_data_sql(), reverse_sql=get_reverse_payment_migrate_data_sql()),
        migrations.RunSQL(get_transaction_migrate_data_sql(), reverse_sql=get_reverse_transaction_migrate_data_sql()),
    ]
