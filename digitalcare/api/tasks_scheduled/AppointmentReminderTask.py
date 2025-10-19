# api/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from ..models import Appointment, DoctorProfile
from ..tasks import create_notification_task  # your notification task

logger = logging.getLogger(__name__)


@shared_task
def send_appointment_reminder(reminder_window_hours=24):
    """
    Sends reminder notifications for confirmed appointments scheduled
    within the next N hours.
    
    Args:
        reminder_window_hours: Hours ahead to check for appointments (default: 24)
    """
    logger.info("=== APPOINTMENT REMINDER TASK STARTED ===")
    
    try:
        now = timezone.now()
        window_end = now + timedelta(hours=reminder_window_hours)
        
        logger.info(f"Checking appointments between {now} and {window_end}")
        
        appointments = Appointment.objects.filter(
            status=Appointment.CONFIRMED,
            scheduled_at__gte=now,
            scheduled_at__lte=window_end
        ).select_related('patient', 'doctor__user', 'facility')
        
        if not appointments.exists():
            logger.info("No confirmed appointments in reminder window")
            return
        
        logger.info(f"Found {appointments.count()} confirmed appointments")
        
        for appointment in appointments:
            try:
                patient = appointment.patient
                doctor_name = (
                    appointment.doctor.user.get_full_name() 
                    or appointment.doctor.user.username 
                    if appointment.doctor 
                    else "your doctor"
                )
                scheduled_local = timezone.localtime(appointment.scheduled_at).strftime("%Y-%m-%d %H:%M %Z")
                
                message = (
                    f"Reminder: Your appointment with Dr. {doctor_name} is scheduled for {scheduled_local}. "
                    f"Please arrive 15 minutes early."
                )
                
                # Send notification
                create_notification_task.delay(patient.id, message)
                logger.info(f"Reminder sent to {patient.username} for appointment at {scheduled_local}")
                
            except Exception as e:
                logger.error(f"Error sending reminder for appointment {appointment.id}: {str(e)}")
                continue
        
        logger.info("=== APPOINTMENT REMINDER TASK COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Unexpected error in appointment reminder task: {str(e)}")
        raise


@shared_task
def send_doctor_appointment_reminder_summary():
    """
    Sends a daily summary notification to each doctor with their
    confirmed and pending appointments for today.
    """
    logger.info("=== DOCTOR APPOINTMENT SUMMARY TASK STARTED ===")
    
    try:
        current_time = timezone.now()
        
        # Get today's date range in local timezone
        local_now = timezone.localtime(current_time)
        start_of_day = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Convert to UTC for database query
        start_utc = start_of_day.astimezone(timezone.utc)
        end_utc = end_of_day.astimezone(timezone.utc)
        
        logger.info(f"Fetching appointments between {start_utc} and {end_utc}")
        
        # Get all doctors with appointments today
        doctors = DoctorProfile.objects.filter(
            appointments__status__in=[Appointment.CONFIRMED, Appointment.PENDING],
            appointments__scheduled_at__gte=start_utc,
            appointments__scheduled_at__lt=end_utc
        ).distinct().select_related('user')
        
        if not doctors.exists():
            logger.info("No doctors with appointments found for today")
            return
        
        logger.info(f"Found {doctors.count()} doctors with appointments")
        
        for doctor in doctors:
            try:
                # Get today's appointments for this doctor
                appointments_today = Appointment.objects.filter(
                    doctor=doctor,
                    scheduled_at__gte=start_utc,
                    scheduled_at__lt=end_utc,
                    status__in=[Appointment.CONFIRMED, Appointment.PENDING]
                )
                
                if not appointments_today.exists():
                    logger.debug(f"No appointments for Dr. {doctor.user.username} today")
                    continue
                
                # Count by status
                confirmed_count = appointments_today.filter(status=Appointment.CONFIRMED).count()
                pending_count = appointments_today.filter(status=Appointment.PENDING).count()
                total_count = appointments_today.count()
                
                message = (
                    f"Good morning Dr. {doctor.user.get_full_name() or doctor.user.username}, "
                    f"you have {total_count} appointments scheduled for today: "
                    f"{confirmed_count} confirmed and {pending_count} pending."
                )
                
                # Send notification to doctor
                if doctor.user:
                    create_notification_task.delay(doctor.user.id, message)
                    logger.info(f"Summary sent to Dr. {doctor.user.username}: {message}")
                else:
                    logger.warning(f"DoctorProfile {doctor.id} has no linked user")
                
            except Exception as e:
                logger.error(f"Error sending summary to doctor {doctor.id}: {str(e)}")
                continue
        
        logger.info("=== DOCTOR APPOINTMENT SUMMARY TASK COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Unexpected error in doctor summary task: {str(e)}")
        raise