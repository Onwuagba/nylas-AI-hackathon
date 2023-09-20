from django.shortcuts import render
from main.models import Annotation
from main.serializer import CustomTokenSerializer, RegistrationSerializer, RetrieveAnnotationSerializer
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt import views as jwt_views
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging
from rest_framework import filters
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

logger = logging.getLogger('server_log')


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


class RetrieveAnnotationView(ListAPIView):
    # permission_classes = (IsAuthenticated,)
    serializer_class = RetrieveAnnotationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['created_at', 'user_email', 'annotation_label']
    search_fields = ['user_email', 'annotation_label', 'text', 'position']
    ordering_fields = ['created_at']

    def get_queryset(self, thread_id):
        try:
            return Annotation.objects.filter(thread_id__iexact=thread_id)
        except Annotation.DoesNotExist:
            raise ValidationError("Thread ID does not exist")

    def get(self, request, **kwargs):
        """
        Retrieves an annotation for a specific thread.

        Returns:
            CustomAPIResponse: The response object containing the annotation, status code, and status.
        """
        thread_id = kwargs.get("thread_id")

        try:
            queryset = self.filter_queryset(self.get_queryset(thread_id))
            if page := self.paginate_queryset(queryset):
                serializer = self.serializer_class(page, many=True)
                query_response = self.get_paginated_response(serializer.data)
                message = query_response.data
                code = status.HTTP_200_OK
                _status = "success"
            else:
                message = "No annotation found for this thread"
                code = status.HTTP_400_BAD_REQUEST
                _status = "failed"
        except Exception as ex:
            logger.error(
                f"Exception in GET RetrieveAnnotation for thread - {thread_id}: {ex}",
                exc_info=True,
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()

class RetrieveAnnotationDetailView(APIView):
    """
    Retrieve, update and delete claim instance
    """
     # permission_classes = (IsAuthenticated,)
    serializer_class = RetrieveAnnotationSerializer

    def get_object(self, id, thread_id):
        try:
            return Annotation.objects.get(id__iexact=id, thread_id__iexact=thread_id, is_deleted=False)
        except:
            raise ValidationError("No annotation found matching the given parameters")

    def get(self, request, **kwargs):
        thread_id = kwargs.get("thread_id")
        annotation_id = kwargs.get("annotation_id")

        try:
            obj = self.get_object(annotation_id, thread_id)
            serializer = self.serializer_class(obj)
            message = serializer.data
            code = status.HTTP_200_OK
            _status = "success"
        except Exception as ex:
            logger.error(
                f"Exception in GET RetrieveAnnotationDetailView with thread id {thread_id} and annotation id {annotation_id}: {ex.args[0]}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()

    def delete(self, request, **kwargs):
        thread_id = kwargs.get("thread_id")
        annotation_id = kwargs.get("annotation_id")

        try:
            obj = self.get_object(annotation_id, thread_id)
            obj.is_deleted = True
            obj.save()
            message = f"Annotation with id {annotation_id} has been deleted successfully"
            code = status.HTTP_200_OK
            _status = "success"
        except Exception as ex:
            logger.error(
                f"Exception in GET RetrieveAnnotationDetailView with thread id {thread_id} and annotation id {annotation_id}: {ex}"
            )
            message = ex.args[0]
            code = status.HTTP_400_BAD_REQUEST
            _status = "failed"

        response = CustomAPIResponse(message, code, _status)
        return response.send()

