from datetime import datetime, timedelta
from django.shortcuts import render
from main.helper import auto_create_annotation, confirm_email_and_participants
from main.models import Annotation, AnnotationComment
from main.serializer import (
    AnnotationCommentDetailSerializer,
    AnnotationCommentSerializer,
    CustomTokenSerializer,
    RegistrationSerializer,
    RetrieveAnnotationSerializer,
)
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt import views as jwt_views
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging
from rest_framework import filters
from rest_framework.views import APIView
from datetime import timezone
from django_filters.rest_framework import DjangoFilterBackend

logger = logging.getLogger("server_log")


class CustomAPIResponse:
    def __init__(self, message, status_code, status):
        self.message = message
        self.status_code = status_code
        self.status = status

    def send(self) -> Response:
        if not all([self.message, self.status_code, self.status]):
            raise ValidationError("message and status code cannot be empty")

        data = {"status": self.status}
        if self.status == "failed":
            if isinstance(self.message, (ValidationError, ValueError)):
                data["message"] = self.message.args[0]
            else:
                data["message"] = self.message
        else:
            data["data"] = self.message
        status_code = self.status_code

        return Response(data, status=status_code)


# Create your views here.
class RegisterAPIView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RegistrationSerializer
    http_method_names = ["post"]

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        try:
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                message = "Registration successful."
                code = status.HTTP_201_CREATED
                _status = "success"
            else:
                message = serializer.errors
                code = status.HTTP_400_BAD_REQUEST
                _status = "failed"
        except Exception as e:
            message = e.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()


class CustomTokenView(jwt_views.TokenObtainPairView):
    serializer_class = CustomTokenSerializer
    token_obtain_pair = jwt_views.TokenObtainPairView.as_view()
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(
                data=request.data,
                context={
                    "request": self.request,
                },
            )
            serializer.is_valid(raise_exception=True)
            return Response(serializer._validated_data, status=status.HTTP_200_OK)
        except TokenError as ex:
            raise InvalidToken(ex.args[0]) from ex
        except (ValidationError, Exception) as exc:
            message = exc.args[0]
            code_status = "failed"
            status_code = (
                status.HTTP_401_UNAUTHORIZED
                if isinstance(exc, ValidationError)
                else status.HTTP_400_BAD_REQUEST
            )

        response = CustomAPIResponse(message, status_code, code_status)
        return response.send()


class RetrieveAnnotationView(ListCreateAPIView):
    http_method_names = ["get", "post"]
    serializer_class = RetrieveAnnotationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["created_at", "user_email", "annotation_label"]
    search_fields = ["user_email", "annotation_label", "text", "position"]
    ordering_fields = ["created_at"]

    def get_queryset(self, email_id):
        try:
            return Annotation.objects.filter(
                email_id__iexact=email_id, is_deleted=False
            )
        except Annotation.DoesNotExist as e:
            raise ValidationError("Email ID does not exist") from e

    def get(self, request, **kwargs):
        """
        Retrieves an annotation for a specific email.

        Returns:
            CustomAPIResponse: The response object containing the annotation, status code, and status.
        """
        email_id = kwargs.get("email_id")

        try:
            queryset = self.filter_queryset(self.get_queryset(email_id))
            if page := self.paginate_queryset(queryset):
                serializer = self.serializer_class(page, many=True)
                query_response = self.get_paginated_response(serializer.data)
                message = query_response.data
                code = status.HTTP_200_OK
                _status = "success"
            else:
                message = "No annotation found for this email"
                code = status.HTTP_400_BAD_REQUEST
                _status = "failed"
        except Exception as ex:
            logger.error(
                f"Exception in GET RetrieveAnnotation for thread - {email_id}: {ex}",
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()

    def post(self, request, **kwargs):
        """create new annotation

        Args:
            text (string): content of the new annotation
            email (string): email address of the annotator
            annotation_label (string): choices defining type of annotation
        """
        email_id = kwargs.get("email_id")
        email = request.data.get("user_email")

        try:
            email_participants = confirm_email_and_participants(email_id)
            print(email_participants)
            if email not in email_participants:
                raise ValidationError(
                    "Annotator email address not a part of this email thread"
                )

            serializer = self.serializer_class(
                data={**request.data, "email_id": email_id}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            message = "Annotation successfully created"
            code = status.HTTP_201_CREATED
            _status = "success"
        except Exception as e:
            message = e.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()


class RetrieveAnnotationDetailView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update and delete annotation instance
    """

    # permission_classes = (IsAuthenticated,)
    http_method_names = ["get", "patch", "delete"]
    serializer_class = RetrieveAnnotationSerializer

    def get_object(self, id, email_id):
        try:
            return Annotation.objects.get(
                id__iexact=id, email_id__iexact=email_id, is_deleted=False
            )
        except:
            raise ValidationError("No annotation found matching the given parameters")

    def get(self, request, **kwargs):
        email_id = kwargs.get("email_id")
        annotation_id = kwargs.get("annotation_id")

        try:
            obj = self.get_object(annotation_id, email_id)
            serializer = self.serializer_class(obj)
            message = serializer.data
            code = status.HTTP_200_OK
            _status = "success"
        except Exception as ex:
            logger.error(
                f"Exception in GET RetrieveAnnotationDetailView with thread id {email_id} and annotation id {annotation_id}: {ex.args[0]}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()

    def patch(self, request, **kwargs):
        email_id = kwargs.get("email_id")
        annotation_id = kwargs.get("annotation_id")
        email = request.data.get("user_email")

        try:
            email_participants = confirm_email_and_participants(email_id)

            if email not in email_participants:
                raise ValidationError(
                    "Annotator email address not a part of this email thread"
                )

            obj = self.get_object(annotation_id, email_id)
            serializer = self.serializer_class(obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            message = "Annotation updated successfully"
            code = status.HTTP_200_OK
            _status = "success"
        except Exception as ex:
            logger.error(
                f"Exception in PATCH RetrieveAnnotationDetailView with id {annotation_id}: {ex}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()

    def delete(self, request, **kwargs):
        email_id = kwargs.get("email_id")
        annotation_id = kwargs.get("annotation_id")

        try:
            obj = self.get_object(annotation_id, email_id)
            obj.is_deleted = True
            obj.save()
            message = (
                f"Annotation with id {annotation_id} has been deleted successfully"
            )
            code = status.HTTP_200_OK
            _status = "success"
        except Exception as ex:
            logger.error(
                f"Exception in GET RetrieveAnnotationDetailView with thread id {email_id} and annotation id {annotation_id}: {ex}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()


class AnnotationCommentView(ListAPIView):
    http_method_names = ["get", "post"]
    serializer_class = AnnotationCommentSerializer

    def get_object(self, annotation_id):
        try:
            return Annotation.objects.get(id__iexact=annotation_id)
        except Annotation.DoesNotExist as ex:
            raise ValidationError("Invalid annotation id") from ex

    def get_queryset(self, annotation_id):
        try:
            return AnnotationComment.objects.filter(annotation__id=annotation_id)
        except Exception as ex:
            raise ValidationError("No comments for given annotation") from ex

    def get(self, request, **kwargs):
        """
        Get comments for a given annotation
        """
        annotation_id = kwargs.get("annotation_id")

        try:
            queryset = self.get_queryset(annotation_id)
            if page := self.paginate_queryset(queryset):
                serializer = self.serializer_class(page, many=True)
                query_response = self.get_paginated_response(serializer.data)
                message = query_response.data
                code = status.HTTP_200_OK
                _status = "success"
            else:
                message = "No comments found for this annotation"
                code = status.HTTP_400_BAD_REQUEST
                _status = "failed"
        except Exception as ex:
            logger.error(
                f"Exception in GET annotationcomment with id {annotation_id}: {ex}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()

    def post(self, request, *args, **kwargs):
        """
        Add comments to a annotation
        """
        email = request.data.get("author_email")

        try:
            obj = self.get_object(kwargs.get("annotation_id"))
            annotation = obj.id
            email_participants = confirm_email_and_participants(obj.email_id)

            if email not in email_participants:
                raise ValidationError(
                    "Annotator email address not a part of this email thread"
                )

            serializer = self.serializer_class(
                data={**request.data, "annotation": annotation}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            message = "Comment posted successfully"
            code = status.HTTP_201_CREATED
            _status = "success"
        except Exception as ex:
            logger.error(
                f"Exception in POST annotationcomment with id {kwargs.get('annotation_id')}: {ex}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()


class AnnotationCommentDetailView(RetrieveUpdateDestroyAPIView):
    http_method_names = ["get", "patch", "delete"]
    serializer_class = AnnotationCommentDetailSerializer

    def get_object(self, annotation_id, comment_id, user):
        try:
            obj = AnnotationComment.objects.get(
                id=comment_id, annotation__id=annotation_id, is_deleted=False
            )
            time_difference = datetime.now(timezone.utc) - obj.created_at
            if time_difference > timedelta(hours=24):
                raise ValidationError("Comments cannot be acted on after 24 hours")
            if obj.author_email != user:
                raise ValidationError("Permission denied")
            return obj
        except AnnotationComment.DoesNotExist as ex:
            raise ValidationError(
                "No comment found matching the given annotation"
            ) from ex

    def get(self, request, **kwargs):
        """
        Get single comment instance for a given annotation
        """
        annotation_id = kwargs.get("annotation_id")
        comment_id = kwargs.get("comment_id")

        try:
            obj = self.get_object(
                annotation_id, comment_id, request.data.get("author_email")
            )  # since we don't manage authentication
            serializer = self.serializer_class(obj)
            message = serializer.data
            code = status.HTTP_200_OK
            _status = "success"
        except Exception as ex:
            logger.error(
                f"Exception in GET AnnotationCommentDetailView with annotation id {annotation_id}, comment id {comment_id}: {ex}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()

    def patch(self, request, *args, **kwargs):
        """
        update comment on an annotation
        """
        annotation_id = kwargs.get("annotation_id")
        comment_id = kwargs.get("comment_id")
        allowed_update_fields = {"comment"}
        email = request.data.get("author_email")

        if not request.data:
            response = CustomAPIResponse(
                "No comment id provided to update",
                status.HTTP_400_BAD_REQUEST,
                "failed",
            )
            return response.send()

        if not set(request.data.keys()).issubset(allowed_update_fields):
            response = CustomAPIResponse(
                "You can only update comment on annotations",
                status.HTTP_400_BAD_REQUEST,
                "failed",
            )
            return response.send()

        try:
            obj = self.get_object(
                annotation_id, comment_id, email
            )  # since we don't manage authentication

            email_participants = confirm_email_and_participants(obj.email_id)
            if email not in email_participants:
                raise ValidationError(
                    "Annotator email address not a part of this email thread"
                )

            serializer = self.serializer_class(obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            message = "Comment updated successfully"
            code = status.HTTP_200_OK
            _status = "success"
        except Exception as ex:
            logger.error(
                f"Exception in PATCH AnnotationCommentDetailView with annotation id {annotation_id}, comment id {comment_id}: {ex}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()

    def delete(self, request, **kwargs):
        """
        delete single comment instance for a given annotation
        """
        annotation_id = kwargs.get("annotation_id")
        comment_id = kwargs.get("comment_id")

        try:
            obj = self.get_object(
                annotation_id, comment_id, request.data.get("author_email")
            )  # since we don't manage authentication
            obj.is_deleted = True
            obj.save()
            message = "Comment deleted successfully"
            code = status.HTTP_200_OK
            _status = "success"
        except Exception as ex:
            logger.error(
                f"Exception in GET AnnotationCommentDetailView with annotation id {annotation_id}, comment id {comment_id}: {ex}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()


class AutoCreateAnnotationView(CreateAPIView):
    """
    create annotation by passing text
    """

    http_method_names = ["post"]

    def check_data(self, data):
        if "text" not in data:
            raise ValidationError("Text is required")

    def post(self, request, *args, **kwargs):
        """
        Create new annotation using AI
        """
        try:
            self.check_data(request.data)
            data = auto_create_annotation(request.data.get("text"))
            message = data
            code = status.HTTP_201_CREATED
            _status = "success"
        except Exception as ex:
            logger.error(f"Exception in POST AutoCreateAnnotationView: {ex}")
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()
