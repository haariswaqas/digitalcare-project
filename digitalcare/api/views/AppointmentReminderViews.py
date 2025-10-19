from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from ..permissions import IsAdminUser
from rest_framework.views import APIView
from ..serializers import AppointmentReminderSerializer, DoctorAppointmentReminderSerializer
from ..task_schedulers import (
    set_appointment_reminder_schedule,
    get_appointment_reminder_schedule,
    set_doctor_appointment_reminder_schedule,
    get_doctor_appointment_reminder_schedule,
    disable_all_appointment_schedules,
    enable_all_appointment_schedules,
    SchedulerError,
)


class AppointmentReminderViewSet(viewsets.ViewSet):
    """Manage appointment reminder schedules"""
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['post'])
    def set_patient_reminder(self, request):
        """Set patient appointment reminder schedule"""
        serializer = AppointmentReminderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = serializer.validated_data
            set_appointment_reminder_schedule(
                every=data['every'],
                period=data['period'],
                enabled=data.get('enabled', True),
                reminder_window_hours=data.get('reminder_window_hours', 24),
            )
            return Response(
                {'detail': 'Patient appointment reminder scheduled successfully'},
                status=status.HTTP_200_OK
            )
        except SchedulerError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def get_patient_reminder(self, request):
        """Get patient appointment reminder schedule"""
        try:
            schedule = get_appointment_reminder_schedule()
            if not schedule:
                return Response(
                    {'detail': 'No patient reminder schedule configured'},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(schedule, status=status.HTTP_200_OK)
        except SchedulerError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def set_doctor_reminder(self, request):
        """Set doctor appointment reminder schedule"""
        serializer = DoctorAppointmentReminderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = serializer.validated_data
            set_doctor_appointment_reminder_schedule(
                hour=data['hour'],
                minute=data['minute'],
                enabled=data.get('enabled', True),
            )
            return Response(
                {'detail': 'Doctor appointment reminder scheduled successfully'},
                status=status.HTTP_200_OK
            )
        except SchedulerError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def get_doctor_reminder(self, request):
        """Get doctor appointment reminder schedule"""
        try:
            schedule = get_doctor_appointment_reminder_schedule()
            if not schedule:
                return Response(
                    {'detail': 'No doctor reminder schedule configured'},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(schedule, status=status.HTTP_200_OK)
        except SchedulerError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def disable_all(self, request):
        """Disable all appointment reminder schedules"""
        try:
            disable_all_appointment_schedules()
            return Response(
                {'detail': 'All appointment reminders disabled'},
                status=status.HTTP_200_OK
            )
        except SchedulerError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def enable_all(self, request):
        """Enable all appointment reminder schedules"""
        try:
            enable_all_appointment_schedules()
            return Response(
                {'detail': 'All appointment reminders enabled'},
                status=status.HTTP_200_OK
            )
        except SchedulerError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)