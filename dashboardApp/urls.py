from django.urls import path
from dashboardApp.views import BillingManagementViews

urlpatterns = [
    path('billing/management/data/', BillingManagementViews.as_view(), name='billing_management'),
]
