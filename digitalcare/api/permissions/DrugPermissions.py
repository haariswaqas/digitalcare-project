from rest_framework.permissions import BasePermission

class DrugPermission(BasePermission):
    """
    Drug model permissions:
    - Admin: full CRUD
    - Facility Admin / Pharmacist: read-only
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.role == "admin":
            return True  # full access
        elif user.role in ["facility_admin", "pharmacist"]:
            return view.action in ["list", "retrieve"]  # read-only
        return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class PharmacyInventoryPermission(BasePermission):
    """
    PharmacyInventory permissions:
    - Facility Admin: full CRUD for their pharmacy
    - Pharmacist: read-only for their assigned pharmacies
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.role in ["facility_admin", "pharmacist"]

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == "facility_admin":
            return obj.pharmacy.admin == user
        elif user.role == "pharmacist":
            return obj.pharmacy.pharmacists.filter(user=user).exists()
        return False

