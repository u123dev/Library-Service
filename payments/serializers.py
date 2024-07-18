from rest_framework import serializers

from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class PaymentSuccessSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255)
