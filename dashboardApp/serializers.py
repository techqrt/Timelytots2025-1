from rest_framework import serializers
from dashboardApp.models import Analytics, BillingManagement


class AnalyticsSerializers(serializers.ModelSerializer):
    class Meta:
        model = Analytics
        fields = '__all__'


class BillingManagementSerializers(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    monthly_subscription_fees = serializers.SerializerMethodField()

    class Meta:
        model = BillingManagement
        fields = '__all__'

    def get_monthly_subscription_fees(self, obj):
        if hasattr(obj.user, 'monthly_subscription_fees') and obj.user.monthly_subscription_fees is not None:
            return obj.user.monthly_subscription_fees
        return 0
