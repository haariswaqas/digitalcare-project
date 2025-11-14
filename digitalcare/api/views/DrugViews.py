# api/views/DrugViews.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from ..models import Drug, PharmacyInventory, Facility
from ..serializers import DrugMiniSerializer, PharmacyInventorySerializer  # or a full Drug serializer if needed
from ..permissions import DrugPermission, PharmacyInventoryPermission


class DrugViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Drugs.
    - Admin: full CRUD
    - Facility Admin / Pharmacist: read-only
    """
    queryset = Drug.objects.all()
    serializer_class = DrugMiniSerializer  # use full serializer if you have one
    permission_classes = [IsAuthenticated, DrugPermission]


class PharmacyInventoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Pharmacy Inventory.
    - Facility Admin: full CRUD for their pharmacy (auto-fills pharmacy)
    - Pharmacist: read-only for their assigned pharmacies
    """
    queryset = PharmacyInventory.objects.all()
    serializer_class = PharmacyInventorySerializer
    permission_classes = [IsAuthenticated, PharmacyInventoryPermission]

    def get_queryset(self):
        user = self.request.user
        if user.role == "facility_admin":
            return self.queryset.filter(pharmacy__admin=user, pharmacy__facility_type=Facility.PHARMACY)
        elif user.role == "pharmacist":
            return self.queryset.filter(pharmacy__pharmacists__user=user, pharmacy__facility_type=Facility.PHARMACY)
        return self.queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "facility_admin":
            facility = getattr(user, "facility", None)
            if not facility:
                raise PermissionDenied("Facility admin does not have an assigned facility.")
            if facility.facility_type != Facility.PHARMACY:
                raise PermissionDenied("The assigned facility is not a pharmacy.")
            serializer.save(pharmacy=facility)
        else:
            raise PermissionDenied("Only facility admins can create inventory items.")