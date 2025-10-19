from rest_framework.serializers import Serializer, IntegerField, ChoiceField, BooleanField


class AppointmentReminderSerializer(Serializer):
    every = IntegerField(min_value=1)
    period = ChoiceField(choices=[
        ('days', 'Days'),
        ('seconds', 'Seconds')
    ])
    enabled = BooleanField()



class DoctorAppointmentReminderSerializer(Serializer):
    hour = IntegerField(min_value=0, max_value=23)
    minute = IntegerField(min_value=0, max_value=59)
    enabled = BooleanField()