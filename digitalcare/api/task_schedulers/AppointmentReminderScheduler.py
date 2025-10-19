from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from django.core.exceptions import ValidationError
import json
import logging

logger = logging.getLogger(__name__)

VALID_PERIODS = {
    'days': IntervalSchedule.DAYS,
    
    'seconds': IntervalSchedule.SECONDS
}

TASK_NAMES = {
    'appointment_reminder': 'Send Appointment Reminders',
    'doctor_reminder': 'Send Doctor Appointment Reminders',
}

TASK_PATHS = {
    'appointment_reminder': 'api.tasks.send_appointment_reminder',
    'doctor_reminder': 'api.tasks.send_doctor_appointment_reminder_summary',
}


class SchedulerError(Exception):
    """Custom exception for scheduler errors"""
    pass


def _validate_period(period: str) -> str:
    """Validate and return period"""
    if period not in VALID_PERIODS:
        raise ValidationError(f"Invalid period. Choose from: {list(VALID_PERIODS.keys())}")
    return period


def _validate_time(hour: int, minute: int) -> tuple:
    """Validate hour and minute"""
    if not (0 <= hour <= 23):
        raise ValidationError("Hour must be between 0 and 23")
    if not (0 <= minute <= 59):
        raise ValidationError("Minute must be between 0 and 59")
    return hour, minute


def set_appointment_reminder_schedule(every: int, period: str, enabled: bool = True, reminder_window_hours: int = 24):
    """
    Set or update appointment reminder schedule.
    
    Args:
        every: Frequency (e.g., 1, 2, 3)
        period: Time period ('days')
        enabled: Whether the task is enabled
        reminder_window_hours: Hours ahead to check for appointments
    """
    try:
        _validate_period(period)
        
        if every < 1:
            raise ValidationError("'every' must be at least 1")
        
        interval, _ = IntervalSchedule.objects.get_or_create(
            every=every,
            period=VALID_PERIODS[period]
        )
        
        PeriodicTask.objects.update_or_create(
            name=TASK_NAMES['appointment_reminder'],
            defaults={
                'interval': interval,
                'task': TASK_PATHS['appointment_reminder'],
                'args': json.dumps([reminder_window_hours]),
                'enabled': enabled,
                'one_off': False,
                'clocked': None,
            }
        )
        
        logger.info(f"Appointment reminder scheduled: every {every} {period}, enabled={enabled}")
        
    except ValidationError as e:
        logger.error(f"Validation error setting appointment reminder: {str(e)}")
        raise SchedulerError(str(e))
    except Exception as e:
        logger.error(f"Unexpected error setting appointment reminder: {str(e)}")
        raise SchedulerError(f"Failed to set appointment reminder: {str(e)}")


def get_appointment_reminder_schedule() -> dict:
    """Get current appointment reminder schedule"""
    try:
        task = PeriodicTask.objects.get(name=TASK_NAMES['appointment_reminder'])
        args = json.loads(task.args or '[]')
        reminder_window = args[0] if args else 24
        
        return {
            'every': task.interval.every,
            'period': task.interval.get_period_display(),
            'enabled': task.enabled,
            'reminder_window_hours': reminder_window,
        }
    except PeriodicTask.DoesNotExist:
        logger.warning("Appointment reminder schedule not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving appointment reminder schedule: {str(e)}")
        raise SchedulerError(f"Failed to retrieve appointment reminder schedule: {str(e)}")


def set_doctor_appointment_reminder_schedule(hour: int, minute: int, enabled: bool = True):
    """
    Set or update doctor appointment reminder schedule (cron-based).
    
    Args:
        hour: Hour of day (0-23)
        minute: Minute of hour (0-59)
        enabled: Whether the task is enabled
    """
    try:
        _validate_time(hour, minute)
        
        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute=minute,
            hour=hour,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='UTC'
        )
        
        PeriodicTask.objects.update_or_create(
            name=TASK_NAMES['doctor_reminder'],
            defaults={
                'crontab': crontab,
                'task': TASK_PATHS['doctor_reminder'],
                'args': json.dumps([]),
                'enabled': enabled,
                'interval': None,
                'one_off': False,
            }
        )
        
        logger.info(f"Doctor appointment reminder scheduled: daily at {hour:02d}:{minute:02d} UTC, enabled={enabled}")
        
    except ValidationError as e:
        logger.error(f"Validation error setting doctor reminder: {str(e)}")
        raise SchedulerError(str(e))
    except Exception as e:
        logger.error(f"Unexpected error setting doctor reminder: {str(e)}")
        raise SchedulerError(f"Failed to set doctor appointment reminder: {str(e)}")


def get_doctor_appointment_reminder_schedule() -> dict:
    """Get current doctor appointment reminder schedule"""
    try:
        task = PeriodicTask.objects.get(name=TASK_NAMES['doctor_reminder'])
        
        return {
            'hour': int(task.crontab.hour),
            'minute': int(task.crontab.minute),
            'enabled': task.enabled,
        }
    except PeriodicTask.DoesNotExist:
        logger.warning("Doctor appointment reminder schedule not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving doctor reminder schedule: {str(e)}")
        raise SchedulerError(f"Failed to retrieve doctor reminder schedule: {str(e)}")


def disable_all_appointment_schedules():
    """Disable all appointment-related schedules"""
    try:
        PeriodicTask.objects.filter(
            name__in=TASK_NAMES.values()
        ).update(enabled=False)
        logger.info("All appointment schedules disabled")
    except Exception as e:
        logger.error(f"Error disabling schedules: {str(e)}")
        raise SchedulerError(f"Failed to disable schedules: {str(e)}")


def enable_all_appointment_schedules():
    """Enable all appointment-related schedules"""
    try:
        PeriodicTask.objects.filter(
            name__in=TASK_NAMES.values()
        ).update(enabled=True)
        logger.info("All appointment schedules enabled")
    except Exception as e:
        logger.error(f"Error enabling schedules: {str(e)}")
        raise SchedulerError(f"Failed to enable schedules: {str(e)}")