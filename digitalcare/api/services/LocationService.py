# api/services/location_service.py
import math
from typing import Optional
from django.db.models import Q, F, Value, FloatField
from django.db.models.functions import ACos, Cos, Radians, Sin
from ..models import DoctorProfile, Facility, PharmacistProfile, LabTechProfile


class LocationService:
    EARTH_RADIUS_KM = 6371

    @staticmethod
    def haversine_distance_expression(lat1: float, lon1: float, lat2_field: str, lon2_field: str):
        """
        Build a Django ORM expression for Haversine distance in kilometers
        between (lat1, lon1) and model fields (lat2_field, lon2_field).
        """
        return (
            LocationService.EARTH_RADIUS_KM *
            ACos(
                Cos(Radians(Value(lat1))) *
                Cos(Radians(F(lat2_field))) *
                Cos(Radians(F(lon2_field)) - Radians(Value(lon1))) +
                Sin(Radians(Value(lat1))) * Sin(Radians(F(lat2_field)))
            )
        )

    # ---------------- FACILITIES ----------------
    @classmethod
    def get_nearby_facilities(
        cls,
        patient_lat: float,
        patient_lon: float,
        radius_km: float = 10,
        facility_type: Optional[str] = None
    ):
        """
        Return a queryset of nearby facilities annotated with distance_km.
        """
        facilities = Facility.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            status="Approved"
        )

        if facility_type:
            facilities = facilities.filter(facility_type=facility_type)

        facilities = facilities.annotate(
            distance_km=cls.haversine_distance_expression(
                patient_lat, patient_lon, "latitude", "longitude"
            )
        ).filter(distance_km__lte=radius_km).order_by("distance_km")

        return facilities

    # ---------------- DOCTORS ----------------
    @classmethod
    def get_nearby_doctors(
        cls,
        patient_lat: float,
        patient_lon: float,
        radius_km: float = 10,
        specialty: Optional[str] = None
    ):
        """
        Return nearby active doctors, optionally filtered by specialty.
        """
        doctors = DoctorProfile.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )

        if specialty:
            doctors = doctors.filter(specialty__icontains=specialty)

        doctors = doctors.annotate(
            distance_km=cls.haversine_distance_expression(
                patient_lat, patient_lon,
                "latitude",
                "longitude"
            )
        ).filter(distance_km__lte=radius_km).order_by("distance_km")

        return doctors

    # ---------------- PHARMACISTS ----------------
    @classmethod
    def get_nearby_pharmacists(
        cls,
        patient_lat: float,
        patient_lon: float,
        radius_km: float = 10
    ):
        """
        Return nearby active pharmacists (no specialty filter).
        """
        pharmacists = PharmacistProfile.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )

        pharmacists = pharmacists.annotate(
            distance_km=cls.haversine_distance_expression(
                patient_lat, patient_lon,
                "latitude",
                "longitude"
            )
        ).filter(distance_km__lte=radius_km).order_by("distance_km")

        return pharmacists

    # ---------------- LAB TECHNICIANS ----------------
    @classmethod
    def get_nearby_lab_techs(
        cls,
        patient_lat: float,
        patient_lon: float,
        radius_km: float = 10
    ):
        """
        Return nearby active laboratory technicians (no specialty filter).
        """
        lab_techs = LabTechProfile.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )

        lab_techs = lab_techs.annotate(
            distance_km=cls.haversine_distance_expression(
                patient_lat, patient_lon,
                "latitude",
                "longitude"
            )
        ).filter(distance_km__lte=radius_km).order_by("distance_km")

        return lab_techs
