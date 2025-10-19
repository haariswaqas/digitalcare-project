from datetime import datetime, timedelta
from django.utils import timezone


class ShiftValidator:
    """
    Utility class to validate appointment bookings against doctor shifts
    """
    
    @staticmethod
    def is_appointment_within_shift(scheduled_at, duration_minutes, doctor, facility):
        """
        Check if the appointment time falls within any of the doctor's shifts
        at the specified facility.
        
        Args:
            scheduled_at: datetime - The scheduled appointment time
            duration_minutes: int - Duration of the appointment
            doctor: DoctorProfile - The doctor
            facility: Facility - The facility where appointment is scheduled
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not scheduled_at or not doctor or not facility:
            return False, "Missing required information"
        
        # Get day of week (0=Monday, 6=Sunday)
        day_of_week = scheduled_at.weekday()
        
        # Get appointment time range
        appt_start_time = scheduled_at.time()
        appt_end_datetime = scheduled_at + timezone.timedelta(minutes=duration_minutes)
        appt_end_time = appt_end_datetime.time()
        
        # Find active shifts for this doctor at this facility on this day
        from ..models import Shift
        shifts = Shift.objects.filter(
            doctor=doctor,
            facility=facility,
            day_of_week=day_of_week,
            is_active=True
        )
        
        if not shifts.exists():
            return False, f"Doctor has no shifts at this facility on {scheduled_at.strftime('%A')}"
        
        # Check if appointment falls within any shift
        for shift in shifts:
            # Handle case where appointment spans across shift boundaries
            if appt_start_time >= shift.start_time and appt_end_time <= shift.end_time:
                return True, "Appointment is within doctor's shift"
            
            # Check if appointment starts in shift but ends after
            if appt_start_time >= shift.start_time and appt_start_time < shift.end_time:
                if appt_end_time > shift.end_time:
                    return False, f"Appointment extends beyond shift end time ({shift.end_time})"
        
        # No valid shift found
        available_times = ", ".join([f"{s.start_time}-{s.end_time}" for s in shifts])
        return False, f"Appointment time not within any shift. Available times: {available_times}"
    
    @staticmethod
    def get_available_slots(doctor, facility, date, slot_duration=30):
        """
        Get available time slots for a doctor at a facility on a specific date
        
        Args:
            doctor: DoctorProfile
            facility: Facility
            date: datetime.date
            slot_duration: int - Duration of each slot in minutes
            
        Returns:
            list of datetime objects representing available slots
        """
        from ..models import Shift
        from ..models import Appointment
        
        day_of_week = date.weekday()
        
        shifts = Shift.objects.filter(
            doctor=doctor,
            facility=facility,
            day_of_week=day_of_week,
            is_active=True
        )
        
        if not shifts.exists():
            return []
        
        available_slots = []
        
        for shift in shifts:
            current_time = datetime.combine(date, shift.start_time)
            end_time = datetime.combine(date, shift.end_time)
            
            while current_time + timedelta(minutes=slot_duration) <= end_time:
                # Check if slot is already booked
                slot_end = current_time + timedelta(minutes=slot_duration)
                
                conflicting_appointments = Appointment.objects.filter(
                    doctor=doctor,
                    facility=facility,
                    scheduled_at__lt=slot_end,
                    scheduled_at__gte=current_time,
                    status__in=['pending', 'confirmed']
                )
                
                if not conflicting_appointments.exists():
                    available_slots.append(current_time)
                
                current_time += timedelta(minutes=slot_duration)
        
        return available_slots
