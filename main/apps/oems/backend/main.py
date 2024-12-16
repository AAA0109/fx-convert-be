import os

import atexit
atexit.register(os._exit, 0)

from main.apps.oems.backend.oms        import OmsBase
from main.apps.oems.backend.ems        import EmsBase
from main.apps.oems.backend.corpay_ems import CorpayEms
from main.apps.oems.backend.rfq_ems    import RfqEms

# =============================================================================

if __name__ == "__main__":

    # import settings

    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help = 'sub-command help', title='subcommands', description='valid subcommands', dest='command')

    # =========================================

    help_parser = subparsers.add_parser('help')

    # ==============================

    oms_parser = subparsers.add_parser('oms', help='OMS Controls')

    oms_parser.add_argument('--oms-id', default='TEST_PAYMENT_OMS1' ) # settings.OMS_ID)
    oms_parser.add_argument('--oms-type', default='CORPAY')
    oms_parser.add_argument('--log-level', default=None)
    oms_parser.add_argument('--regen', action='store_true', default=False)
    oms_parser.add_argument('--queue-name', default='global1')
    oms_parser.add_argument('--batch-size', type=int, default=1)

    ems_parser = subparsers.add_parser('ems', help='EMS Controls')

    ems_parser.add_argument('--ems-id', default='CORPAY1' ) # settings.OMS_ID)
    ems_parser.add_argument('--ems-type', default='CORPAY')
    ems_parser.add_argument('--log-level', default=None)
    ems_parser.add_argument('--regen', action='store_true', default=False)
    ems_parser.add_argument('--queue-name', default='global1')
    ems_parser.add_argument('--batch-size', type=int, default=1)

    args = parser.parse_args()
    command = args.command

    # ==========================

    if command == 'help':
        parser.print_help()
    elif command == 'oms':
        obj = OmsBase
        server = obj( args.oms_id, args.oms_type, log_level=args.log_level, regen=args.regen, queue_name=args.queue_name, batch_size=args.batch_size )
        server.run()
    elif command == 'ems':
        if args.ems_type == 'CORPAY':
            obj = CorpayEms
        elif args.ems_type == 'RFQ':
            obj = RfqEms
        else:
            raise ValueError
            obj = EmsBase
        server = obj( args.ems_id, args.ems_type, log_level=args.log_level, regen=args.regen, queue_name=args.queue_name, batch_size=args.batch_size )
        server.run()

