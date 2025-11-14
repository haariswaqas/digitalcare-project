# api/permissions/prescription_permissions.py
from rest_framework.permissions import BasePermission


class PrescriptionPermission(BasePermission):
    """
    Prescription permissions:
    - Doctor: CRUD their own prescriptions
    - Patient: read-only their own
    - Pharmacist: read-only for prescriptions in their pharmacy
    - Facility Admin: read-only for prescriptions in their pharmacy
    """
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated if user else False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == "doctor":
            return obj.doctor.user == user
        elif user.role == "patient":
            return getattr(obj.patient, "user", None) == user
        elif user.role == "pharmacist":
            return obj.items.filter(
                drug__pharmacy_stocks__pharmacy__pharmacists__user=user
            ).exists()
        elif user.role == "facility_admin":
            return obj.items.filter(
                drug__pharmacy_stocks__pharmacy__admin=user
            ).exists()
        return False


class PrescriptionItemPermission(BasePermission):
    """
    PrescriptionItem permissions:
    - Doctor: read/write items for their prescriptions
    - Patient: read-only
    - Pharmacist: read-only for their pharmacy
    - Facility Admin: read-only for their pharmacy
    """
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated if user else False

    def has_object_permission(self, request, view, obj):
        presc = obj.prescription
        user = request.user
        if user.role == "doctor":
            return presc.doctor.user == user
        elif user.role == "patient":
            return getattr(presc.patient, "user", None) == user
        elif user.role == "pharmacist":
            return obj.drug.pharmacy_stocks.filter(pharmacy__pharmacists__user=user).exists()
        elif user.role == "facility_admin":
            return obj.drug.pharmacy_stocks.filter(pharmacy__admin=user).exists()
        return False