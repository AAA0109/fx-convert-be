from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.response import Response
import requests

from main.apps.marketing.api.serializers.models.marketing import (
    FxCalculatorSerializer,
    FxCalculatorResponseSerializer,
    DemoFormRequestSerializer,
    DemoResponseSerializer
)

from main.apps.hubspot.services.company import HubSpotCompanyService

from main.apps.hubspot.services.contact import HubSpotContactService

# ==========================
# Marketing Views
# ==========================

class FetchCurrencyRateApiView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=FxCalculatorSerializer,
        responses={status.HTTP_200_OK: FxCalculatorResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        try:
            data = request.POST
            serializer = FxCalculatorSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            url = "https://wise.com/gateway/v3/quotes/"
            serializer_data = serializer.validated_data

            payload = {
                "sourceAmount": serializer_data.get("sourceAmount"),
                "sourceCurrency": serializer_data.get("sourceCurrency"),
                "targetCurrency": serializer_data.get("targetCurrency"),
                "guaranteedTargetAmount": False,
                "type": "REGULAR",
            }
            headers = {"Content-Type": "application/json"}

            response = requests.post(url, json=payload, headers=headers)
            
            payment_options_data = response.json().get("paymentOptions", [])
            serializer = FxCalculatorResponseSerializer(data=payment_options_data[0])
            serializer.is_valid(raise_exception=True)

            if response.status_code == 200:
                return Response(serializer.validated_data, status=200)
            else:
                return Response(
                    {"error": "Failed to fetch data"}, status=response.status_code
                )
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class SendMappedDemoForm(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=DemoFormRequestSerializer,
        responses={status.HTTP_200_OK: DemoResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            serializer = DemoFormRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.hs_company_service = HubSpotCompanyService()
            self.hs_contact_service = HubSpotContactService()

            contact_data = {
                "firstname": data["name"],
                "email": data["email"],
                "jobtitle": data["jobtitle"],
                "friend_referral": data["friend_referral"],
                "company": data["company"],
            }

            company_data = {
                "remote_work": data["do_you_have_employees_living_working_internationally_"],
                "name": data["company"],
                "domain": data["company_url"],
                "currencies": data["currencies"],
                "annual_international_transaction_volume": data["annual_international_transaction_volume"],
            }

            contact_response = self.hs_contact_service.create_contact(contact_data)
            company_response = self.hs_company_service.create_company(company_data)

            response_serializer = DemoResponseSerializer(data={"success": True, "contact_id": contact_response.to_dict().get("id"), "company_id": company_response.to_dict().get("id")
            })
            response_serializer.is_valid(raise_exception=True)
            
            return Response(response_serializer.validated_data , status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)