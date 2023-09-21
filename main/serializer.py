import contextlib

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from rest_framework import serializers, exceptions
from rest_framework_simplejwt import serializers as jwt_serializers

from main.models import Annotation, AnnotationComment
import logging

logger = logging.getLogger("server_log")


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True,
        required=True,
        validators=[validate_password],
    )
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = get_user_model()
        exclude = [
            "regToken",
        ]
        read_only_fields = [
            "groups",
            "user_permissions",
            "is_superuser",
            "is_staff",
            "is_deleted",
            "is_active",
            "last_login",
            "date_joined",
        ]

    def validate(self, data):
        if not data.get("password") or not data.get("confirm_password"):
            raise serializers.ValidationError("Please enter a password and confirm it")
        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError("Your passwords do not match")

        return data

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        validated_data.pop("confirm_password", None)

        user = self.Meta.model(**validated_data)

        user.set_password(password)
        user.save()

        return user


class CustomTokenSerializer(jwt_serializers.TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["first_name"] = user.first_name
        token["last_name"] = user.last_name
        return token

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        with contextlib.suppress(KeyError):
            authenticate_kwargs["request"] = self.context["request"]
        self.user = authenticate(**authenticate_kwargs)
        if self.user is None or not self.user.is_active:
            error = {
                "message": "No account found with this credential",
                "status": "Failed",
            }
            raise exceptions.AuthenticationFailed(error)
        return super().validate(attrs)


class RetrieveAnnotationSerializer(serializers.ModelSerializer):
    date_created = serializers.SerializerMethodField(source="created_at")

    class Meta:
        model = Annotation
        fields = [
            "id",
            "text",
            "position",
            "user_email",
            "annotation_label",
            "date_created",
            "is_deleted",
        ]

    def get_date_created(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")


class AnnotationCommentSerializer(serializers.ModelSerializer):
    date_created = serializers.SerializerMethodField(source="created_at")

    class Meta:
        model = AnnotationComment
        fields = ["annotation", "comment", "author_email", "date_created"]

    def get_date_created(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def create(self, validated_data):
        try:
            query = self.Meta.model.objects.create(**validated_data)
            query.save()

            return query
        except IntegrityError as ex:
            logger.error("An error occurred: %s", ex)
            if "unique constraint" in str(ex.args):
                raise serializers.ValidationError(
                    f"Duplicate comment by {validated_data.get('author_email')} on this annotation"
                ) from ex
        except Exception as e:
            logger.error("An error occurred: %s", e)
            raise serializers.ValidationError("Oops! Something went wrong") from e
