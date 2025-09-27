from rest_framework import serializers
from ..models import Facility, User

class FacilitySerializer(serializers.ModelSerializer):
    admin_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='facility_admin'),
        source='admin',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Facility
        fields = [
            'id', 'name', 'facility_type', 'address', 'phone',
            'latitude', 'longitude', 'is_partner', 'status', 'admin', 'admin_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'admin']

    def create(self, validated_data):
        admin_user = validated_data.pop('admin', None)
        facility = Facility.objects.create(**validated_data)
        if admin_user:
            facility.admin = admin_user
            facility.save()
        return facility

    def update(self, instance, validated_data):
        admin_user = validated_data.pop('admin', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if admin_user:
            instance.admin = admin_user
        instance.save()
        return instance
