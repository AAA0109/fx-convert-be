import os
import sys

# Disable those annoying warnings
import urllib3

urllib3.disable_warnings()


def run():
    from main.apps.oems.services.connector.oems import OEMSEngineAPIConnector, OEMSQueryAPIConnector

    oems_query_api = OEMSQueryAPIConnector()
    oems_engine_api = OEMSEngineAPIConnector()

    try:
        health = oems_engine_api.oms_health()
        print(f"Health: {health}")

        # if req["Type"] == "ERROR":
        #     print(f"Ticket was {req['Action']}, reason: {req['Msg']}")

        tickets = oems_query_api.get_tickets()
        print(f"TICKETS: {tickets}")

        fills = oems_query_api.get_fills()
        print(f"FILLS: {fills}")

        orders = oems_query_api.get_orders()
        print(f"ORDERS: {len(orders)}")
        for order in orders:
            if order["RemainQty"] == 0:
                print(f"Finished with order for {order['Qty']} units of {order['Market']}")
            else:
                print(f"Filled {order['Done']}, remains {order['RemainQty']} of {order['Market']}")

    except RuntimeError as ex:
        print(f"ERROR: {ex}")


if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
