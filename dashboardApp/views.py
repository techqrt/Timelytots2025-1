from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from datetime import datetime

from dashboardApp.models import BillingManagement
from dashboardApp.serializers import BillingManagementSerializers


class BillingManagementViews(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            # Fetch billing records belonging to the logged-in user
            billing_records = BillingManagement.objects.filter(user=request.user)

            # Filter by start_date and end_date if provided
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    billing_records = billing_records.filter(start_date__gte=start_date_obj)
                except ValueError:
                    return Response(
                        {'error': 'Invalid start_date format. Use YYYY-MM-DD'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    billing_records = billing_records.filter(end_date__lte=end_date_obj)
                except ValueError:
                    return Response(
                        {'error': 'Invalid end_date format. Use YYYY-MM-DD'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if billing_records.exists():
                serializer = BillingManagementSerializers(billing_records, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'No billing record found.'}, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
