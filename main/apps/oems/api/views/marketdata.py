
from rest_framework.views import APIView

# perm stuff
from rest_framework.permissions import IsAuthenticated
from main.apps.core.utils.api import HasCompanyAssociated, UserBelongsToCompany

from main.apps.oems.api.utils.response import ErrorResponse, Response

# TODO: add row based throttling

class DataFrameView(APIView):
	permission_classes = [IsAuthenticated, HasCompanyAssociated]

	db_table = 'market_data_corpay_spot'
	index_field = 'date'
	df_fields   = ['date','rate','rate_ask','rate_bid']

	def get(self, request, format=None):
		# support sampling
		# select flds from db_table where query_params
		# select a way to query for panels
		pass

		