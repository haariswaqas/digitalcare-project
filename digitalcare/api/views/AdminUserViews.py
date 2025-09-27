from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from ..models import User, Otp
from ..serializers import AdminUserSerializer
from ..tasks import send_email_task


class AdminUserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        raw_password = self.request.data.get('password')
        user = serializer.save()
        user.set_password(raw_password)
        user.save()

        otp_code = Otp.generate_otp()
        # Only create OTP if it doesn't exist
        Otp.objects.update_or_create(
            user=user,
            defaults={"code": otp_code, "is_verified": True}
        )

        subject = "Welcome to DigitalCare!"
        message = (
            f"Dear {user.username},\n\n"
            "You have been added to DigitalCare by an administrator. Here are your login credentials:\n\n"
            f"Email: {user.email}\nPassword: {raw_password}\n\n"
            "Please log in and update your password immediately after your first login.\n\n"
            "DigitalCare connects hospitals, pharmacies, and clinics for seamless healthcare management.\n\n"
            "Best regards,\nThe DigitalCare Team"
        )
        send_email_task.delay(subject, message, [user.email])

    def destroy(self, request, *args, **kwargs):
        """Override to send an email before deleting a user."""
        user = self.get_object()
        subject = "Your DigitalCare Account Has Been Deleted"
        message = (
            f"Dear {user.username},\n\n"
            "Your account on DigitalCare has been deleted by an administrator. "
            "If you believe this is a mistake, please contact support immediately.\n\n"
            "Best regards,\nThe DigitalCare Team"
        )
        send_email_task.delay(subject, message, [user.email])
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user.status != User.BANNED:
            user.status = User.BANNED
            user.save()
            subject = "Your DigitalCare Account Has Been Suspended"
            message = (
                f"Dear {user.username},\n\n"
                "Your access to DigitalCare has been suspended by an administrator. "
                "You will not be able to log in until your account is reactivated.\n\n"
                "If you believe this is an error, please contact support.\n\n"
                "Best regards,\nThe DigitalCare Team"
            )
            send_email_task.delay(subject, message, [user.email])
            return Response({"status": "user banned"}, status=status.HTTP_200_OK)
        else:
            return Response({"status": "user is already banned"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        if user.status == User.BANNED:
            user.status = User.ACTIVE
            user.save()
            subject = "Your DigitalCare Account is Active"
            message = (
                f"Dear {user.username},\n\n"
                "Your DigitalCare account has been activated by an administrator. "
                "You can now log in and access the platform.\n\n"
                "DigitalCare supports hospitals, pharmacies, and clinics to provide seamless healthcare services.\n\n"
                "Best regards,\nThe DigitalCare Team"
            )
            send_email_task.delay(subject, message, [user.email])
            return Response({"status": "user is active now"}, status=status.HTTP_200_OK)
        else:
            return Response({"status": "user is already active"}, status=status.HTTP_400_BAD_REQUEST)
