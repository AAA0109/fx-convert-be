from operator import or_, and_
from functools import reduce

from django.db.models import Q

class MultiTermAndSearchMixin:

	def get_search_results(self, request, queryset, search_term):
		search_words = search_term.split(',')
		if search_words:
			final_query = []
			for word in search_words:
				q_objects = reduce(or_, [Q(**{field + '__icontains': word.strip()})
								for field in self.search_fields])
				final_query.append(q_objects)
			queryset = queryset.filter(reduce(and_, final_query))
			use_distinct = True
		else:
			queryset, use_distinct = super().get_search_results(
											   request, queryset, search_term)
		return queryset, use_distinct
