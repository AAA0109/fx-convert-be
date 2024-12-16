from abc import ABC, abstractmethod


class BaseProvider(ABC):

    @abstractmethod
    def get_ids(self):
        raise NotImplementedError

    @staticmethod
    def get_ids_from_queryset(qs):
        return list(qs.values_list('id', flat=True))
