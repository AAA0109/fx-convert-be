from abc import abstractmethod
from urllib.parse import urlparse, urlencode, parse_qs

from drf_spectacular.utils import extend_schema, \
    OpenApiParameter
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from main.apps.ibkr.api.serializers.eca import IBApplicationsSerializer, IBApplicationsSuccessResponseSerializer, \
    IBApplicationsErrorResponseSerializer, IBAccountStatusRequestSerializer, IBAccountStatusesResponseSerializer, \
    IBAccountStatusResponseSerializer, CreateECASSOSerializer, CreateECASSOResponseSerializer, TasksRequestSerialiezr, \
    PendingTasksResponseSerializer, RegistrationTasksResponseSerializer
from main.apps.ibkr.models import Application
from main.apps.ibkr.services.eca.eca import IBECAService


class IBECAViewMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ib_application_service = IBECAService()


class CreateIBApplicationView(IBECAViewMixin, generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = IBApplicationsSerializer

    @extend_schema(
        request=IBApplicationsSerializer,
        responses={
            status.HTTP_200_OK: IBApplicationsSuccessResponseSerializer,
            status.HTTP_400_BAD_REQUEST: IBApplicationsErrorResponseSerializer
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        response_status, response_data = self.ib_application_service.create_application_for_user(
            request.user,
            serializer.validated_data
        )
        if response_status == 'Error':
            serializer = IBApplicationsErrorResponseSerializer({"status": response_status, "errors": response_data})
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
        if response_status == 'Success':
            external_id = response_data['external_id']
            user = response_data['user']
            user_id = response_data['user_id']
            account = response_data['account']
            entity = response_data['entity']
            application = Application(
                external_id=external_id,
                company=request.user.company,
                username=user,
                user_id=user_id,
                account=account,
                entity=entity
            )
            application.save()

        serializer = IBApplicationsSuccessResponseSerializer({"status": response_status})
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetIBAccountStatusesView(IBECAViewMixin, generics.ListAPIView):
    """
    Service to query status of account(s).
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = IBAccountStatusRequestSerializer
    pagination_class = None
    filter_backends = []

    @extend_schema(
        parameters=[IBAccountStatusRequestSerializer],
        responses={
            status.HTTP_200_OK: IBAccountStatusesResponseSerializer()
        }
    )
    def list(self, request: Request, *args, **kwargs):
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        status_param = serializer.validated_data.get('status')
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        response = self.ib_application_service.get_account_status(start_date=start_date, end_date=end_date,
                                                                  status=status_param)

        serializer = IBAccountStatusesResponseSerializer(response)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetIBAccountStatusView(IBECAViewMixin, generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = IBAccountStatusResponseSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='broker_account_id', description='Broker Account ID', type=str)
        ]
    )
    def get(self, request, *args, **kwargs):
        broker_account_id = request.query_params.get('broker_account_id')
        response = self.ib_application_service.get_account_status(account_ids=[broker_account_id])
        response_serializer = IBAccountStatusResponseSerializer(response)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class CreateECASSOView(IBECAViewMixin, generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CreateECASSOSerializer

    @extend_schema(
        request=CreateECASSOSerializer,
        responses={
            status.HTTP_200_OK: CreateECASSOResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        url = self.ib_application_service.get_sso_create_url(data['credential'], data['ip'])
        if url is None:
            return Response({
                "details": "Unable to get SSO create URL from IBKR"
            }, status.HTTP_400_BAD_REQUEST)
        url = url.decode()
        if data.get('action'):
            action = data.get('action')
            action_param = dict(CreateECASSOSerializer.ACTIONS)[action]
            url = self._add_action_param_to_url(url, action_param)
        response_serializer = CreateECASSOResponseSerializer({
            "url": url
        })
        return Response(response_serializer.data, status.HTTP_200_OK)

    @staticmethod
    def _add_action_param_to_url(url, action_param):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        query_params['ACTION'] = action_param
        encoded_params = urlencode(query_params, doseq=True)
        updated_url = parsed_url._replace(query=encoded_params).geturl()
        return updated_url


class GetTasksView(IBECAViewMixin, generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    filterset_fields = ['broker_account_id', 'form_number']
    serializer_class = TasksRequestSerialiezr
    pagination_class = None
    filter_backends = []
    task_type = None

    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        broker_account_id = serializer.validated_data.get('broker_account_id')
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        form_number = serializer.validated_data.get('form_number')
        if self.task_type is None:
            raise ValueError("Undefined task type")
        response = self.ib_application_service.get_tasks(self.task_type, broker_account_id, start_date, end_date,
                                                         form_number)

        return self.handle_task_response(response)

    @abstractmethod
    def handle_task_response(self, response: Response):
        raise NotImplementedError("Undefined handle_task_response")


class GetPendingTasksView(GetTasksView):
    task_type = 'pending'

    @extend_schema(
        parameters=[TasksRequestSerialiezr],
        responses={
            status.HTTP_200_OK: PendingTasksResponseSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def handle_task_response(self, response):
        data = response[0]
        if type(data['pendingTasks']) is not list:
            pending_tasks = [data['pendingTasks']]
            data['pendingTasks'] = pending_tasks
        serializer = PendingTasksResponseSerializer(data=response[0])
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetRegistrationTasksView(GetTasksView):
    task_type = 'registration'

    @extend_schema(
        parameters=[TasksRequestSerialiezr],
        responses={
            status.HTTP_200_OK: RegistrationTasksResponseSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def handle_task_response(self, response):
        data = response[0]
        if type(data['registrationTasks']) is not list:
            registration_tasks = [data['registrationTasks']]
            data['registrationTasks'] = registration_tasks
        serializer = RegistrationTasksResponseSerializer(data=response[0])
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
