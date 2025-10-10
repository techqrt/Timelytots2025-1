from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from dashboardApp.models import BillingManagement
from dashboardApp.serializers import BillingManagementSerializers


class BillingManagementViews(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            # Fetch billing records belonging to the logged-in user
            billing_records = BillingManagement.objects.filter(user=request.user)

            if billing_records.exists():
                serializer = BillingManagementSerializers(billing_records, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'No billing record found.'}, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
