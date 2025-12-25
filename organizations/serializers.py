from rest_framework import serializers
from .models import Organization

class OrganizationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name")
