from django.urls import path

from main.views import (
    AnnotationCommentDetailView,
    AnnotationCommentView,
    RetrieveAnnotationDetailView,
    RetrieveAnnotationView,
)

app_name = "main"

urlpatterns = [
    path("threads/<str:thread_id>/annotation/", RetrieveAnnotationView.as_view()),
    path(
        "threads/<str:thread_id>/annotation/<str:annotation_id>/",
        RetrieveAnnotationDetailView.as_view(),
    ),
    path(
        "threads/annotation/<str:annotation_id>/comment/",
        AnnotationCommentView.as_view(),
    ),
    path(
        "threads/annotation/<str:annotation_id>/comment/<int:comment_id>/",
        AnnotationCommentDetailView.as_view(),
    ),
]
