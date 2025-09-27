from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from ..models import User, VideoConsultation
from ..services import TwilioProvider




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_consultation(request):
    """
    Patient initiates a consultation request to a doctor.
    Body: { "doctor_id": int, "scheduled_at": optional ISO datetime }
    """
    user = request.user
    if user.role not in ["student", "adult", "visitor"]:
        return Response({"error": "Only patients can request consultations"},
                        status=status.HTTP_403_FORBIDDEN)

    doctor_id = request.data.get("doctor_id")
    if not doctor_id:
        return Response({"error": "doctor_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    doctor = get_object_or_404(User, id=doctor_id, role="doctor")

    consult = VideoConsultation.objects.create(
        patient=user,
        doctor=doctor,
        provider_kind="twilio"
    )
    # TODO: notify doctor via push/socket
    return Response({"id": consult.id, "status": consult.status}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_consultation(request, consult_id):
    """
    Doctor accepts a consultation -> generate room + tokens and return them.
    """
    user = request.user
    consult = get_object_or_404(VideoConsultation, id=consult_id)

    if consult.doctor != user:
        return Response({"error": "Only the assigned doctor can accept"},
                        status=status.HTTP_403_FORBIDDEN)

    provider = TwilioProvider()
    room = provider.create_room_name(consult)

    # Generate tokens
    doctor_token = provider.generate_token(identity=f"doctor-{consult.doctor.id}", room=room)
    patient_token = provider.generate_token(identity=f"patient-{consult.patient.id}", room=room)

    consult.provider_room = room
    consult.status = "accepted"
    consult.metadata.update({"tokens": {"doctor": doctor_token, "patient": patient_token}})
    consult.save()

    return Response({
        "room": room,
        "doctor_token": doctor_token,
        "patient_token": patient_token,
        "consult_id": consult.id
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_consultation(request, consult_id):
    """
    Returns a token/room for the current authenticated user (doctor or patient).
    """
    user = request.user
    consult = get_object_or_404(VideoConsultation, id=consult_id)
    provider = TwilioProvider()

    if consult.doctor == user:
        role = "doctor"
        identity = f"doctor-{consult.doctor.id}"
    elif consult.patient == user:
        role = "patient"
        identity = f"patient-{consult.patient.id}"
    else:
        return Response({"error": "Not authorized for this consultation"},
                        status=status.HTTP_403_FORBIDDEN)

    room = consult.provider_room or provider.create_room_name(consult)
    token = provider.generate_token(identity=identity, room=room)

    consult.metadata.setdefault("join_tokens", {}).update({identity: {"issued": True}})
    consult.save()

    return Response({"room": room, "token": token, "role": role}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_consultation(request, consult_id):
    """
    Mark consult finished. Patients or doctors can call this.
    """
    user = request.user
    consult = get_object_or_404(VideoConsultation, id=consult_id)

    if consult.doctor != user and consult.patient != user:
        return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

    consult.status = "finished"
    consult.save()
    return Response({"message": "Consultation ended"}, status=status.HTTP_200_OK)
