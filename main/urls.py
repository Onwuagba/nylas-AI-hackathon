from django.urls import path

from main.views import RetrieveAnnotationView

app_name = "main"

urlpatterns = [
    path("threads/<str:thread_id>/annotation/", RetrieveAnnotationView.as_view()),
]
