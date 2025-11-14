from rest_framework import serializers
from ..models import Drug, PharmacyInventory, Facility

class DrugMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = ["id", "name", "form", "strength"]  # adjust based on your Drug model


class PharmacyInventorySerializer(serializers.ModelSerializer):
    drug = DrugMiniSerializer(read_only=True)
    drug_id = serializers.PrimaryKeyRelatedField(
        queryset=Drug.objects.all(), write_only=True, source='drug'
    )
    pharmacy = serializers.PrimaryKeyRelatedField(read_only=True) 
    class Meta:
        model = PharmacyInventory
        fields = [
            "id",
            "pharmacy",
            "drug",
            "drug_id",
            "quantity",
            "unit_price",
            "last_updated",
        ]
        read_only_fields = ["id", "last_updated"]

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user and getattr(user, "role", None) == "facility_admin":
            try:
                # Auto-fill the pharmacy field with the facility owned by this admin
                validated_data["pharmacy"] = Facility.objects.get(admin=user, facility_type="pharmacy")
            except Facility.DoesNotExist:
                raise serializers.ValidationError("You do not have a pharmacy assigned as a facility admin.")

        return super().create(validated_data)