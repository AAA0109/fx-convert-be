import logging

from django.core.management.base import BaseCommand

from main.apps.oems.services.connector.oems import OEMSEngineAPIConnector

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        pass


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to check if OEMS services are healthy"

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        parser.add_argument("--oms_health", type=int, help="Optional: Check OMS health (Default=True)")
        parser.add_argument("--ems_health", type=int, help="Optional: Check EMS health (Default=True)")
        parser.add_argument("--fix_health", type=int, help="Optional: Check FIX health (Default=True)")
        parser.add_argument("--raise_exception", type=int, help="Optional: Raise exception if health "
                                                                "check fails (Default=False)")

    def handle(self, *args, **options):
        oms_health = bool(options["oms_health"])
        ems_health = bool(options["ems_health"])
        fix_health = bool(options["fix_health"])
        raise_exception = bool(options["raise_exception"])

        try:
            oems_engine_api: OEMSEngineAPIConnector = OEMSEngineAPIConnector()

            if not any([oms_health, ems_health, fix_health]):
                oms_health = ems_health = fix_health = True

            logger.debug(f"Checking health services for oms_health={oms_health} "
                        f"ems_health={ems_health} and fix_health={fix_health}")

            if oms_health:
                oms_health_check = oems_engine_api.oms_health()
                logger.debug(oms_health_check)
                if raise_exception and oms_health['Action'] != "Alive":
                    raise Exception("Fix_health_check failed!")

            if ems_health:
                ems_health_check = oems_engine_api.ems_health()
                logger.debug(ems_health_check)
                if raise_exception and ems_health['Action'] != "Alive":
                    raise Exception("Fix_health_check failed!")

            if fix_health:
                fix_health_check = oems_engine_api.fix_health()
                logger.debug(fix_health_check)
                if raise_exception and fix_health_check['Action'] != "Alive":
                    raise Exception("Fix_health_check failed!")

            logger.debug("Services are healthy!")
            logger.debug("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            logger.debug("Services are not healthy")
            if raise_exception:
                raise Exception(ex)
