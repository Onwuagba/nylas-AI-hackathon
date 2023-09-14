from django.shortcuts import render
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from main.serializer import RegistrationSerializer, CustomTokenSerializer
from rest_framework_simplejwt import views as jwt_views
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken


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
