# VideoConsultationUrls.py
from django.urls import path
from ..views import VideoConsultationViews


urlpatterns = [
    path("video-consultation/", VideoConsultationViews.create_consultation, name="create_consultation"),
    path("video-consultation/<int:consult_id>/accept/", VideoConsultationViews.accept_consultation, name="accept_consultation"),
    path("video-consultation/<int:consult_id>/join/", VideoConsultationViews.join_consultation, name="join_consultation"),
    path("video-consultation/<int:consult_id>/end/", VideoConsultationViews.end_consultation, name="end_consultation"),
]
