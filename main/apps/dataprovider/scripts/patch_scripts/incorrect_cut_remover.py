from main.apps.dataprovider.scripts.utils import get_revision_df
from main.apps.marketdata.models import DataCut


class IncorrectCutRemover(object):

    def __init__(self):
        self.revision_df, _ = get_revision_df()

    def execute(self):
        qs_removed = DataCut.objects.filter(id__in=self.revision_df["data_cut_id"].tolist())
        print(f"Removed {qs_removed.count()} incorrect data cuts.")
        qs_removed.delete()
