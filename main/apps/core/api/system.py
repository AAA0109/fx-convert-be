from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from main.apps.core.auth.permissions import IsInternalSystemUser


class SystemAPIOnlyView(APIView):
    """
    Service to expose system api only
    """
    permission_classes = (IsAuthenticated, IsInternalSystemUser,)
