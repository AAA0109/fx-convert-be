from django.core.exceptions import ValidationError
from django.db.models import Q
import operator
from functools import reduce

from django.http import Http404
from django.shortcuts import get_object_or_404


class MultipleFieldLookupMixin(object):
    def get_object(self):
        queryset = self.get_queryset()  # Get the base queryset
        queryset = self.filter_queryset(queryset)  # Apply any filter backends
        obj = None

        for field in self.lookup_fields:
            lookup_value = self.kwargs.get(self.lookup_field)
            if lookup_value:
                try:
                    obj = get_object_or_404(queryset, **{field: lookup_value})
                    break  # Break out of the loop if an object is found
                except ValidationError as e:
                    # Handle the case where the lookup value is an invalid UUID
                    continue

        if obj is None:
            raise Http404("No object found with the provided lookup values.")

        self.check_object_permissions(self.request, obj)
        return obj
