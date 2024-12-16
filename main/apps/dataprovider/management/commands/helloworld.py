from django.core.management.base import BaseCommand



class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument('--job_id', type=str, help='Optional: JOB_ID to be used by pipelines.')

class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = 'Hello world!'

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        parser.add_argument('--data', type=str, help='Optional: pass any JSON object as string.')

    def handle(self, *args, **options):
        print(f"Hello World - your job_id is {options['job_id']}")

        try:
            print("Command executed successfully!")
        except Exception as ex:
            print(ex)
            raise Exception(ex)
