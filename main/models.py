import re
import uuid, base58

from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from main.constants import ANNOTATION


def validate_name(value):
    # This pattern allows letters, spaces, hyphens, and apostrophes.
    pattern = r"^[A-Za-z\s'-]+$"

    if not re.match(pattern, value):
        raise ValidationError("Enter a valid first name.")


def validate_phone_number(value):
    """
    Validate a phone number.

    :param value: A string representing the phone number to be validated.
    :raises ValidationError: If the phone number is not valid.
    """
    if value and str(value).startswith("+"):
        value = f"0{str(value)[4:]}"

    if not re.match(r"^\d{11}$", value):
        raise ValidationError("Invalid phone number. Must be 11 digits.")


username_validator = UnicodeUsernameValidator()


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(
        _("Deactivate Account"),
        default=False,
        help_text=_("Designates whether this entry has been deleted."),
    )

    class Meta:
        abstract = True
        ordering = ["-created_at", "-updated_at"]


class CustomAdminManager(BaseUserManager):
    """relevant for admin to still see soft-deleted users
    that is hidden via the UserManager class below."""

    pass


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email and not username:
            raise ValueError("Email and username is required")

        user = self.model(
            email=self.normalize_email(email),
            username=username,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if password is None:
            raise TypeError("Superusers must have a password.")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, username, password, **extra_fields)

    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(is_deleted=False)


class UserAccount(AbstractUser, PermissionsMixin, BaseModel):
    uid = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, primary_key=True
    )
    username = None
    first_name = models.CharField(
        max_length=50, validators=[validate_name], null=False, blank=False
    )
    last_name = models.CharField(
        max_length=50, validators=[validate_name], null=False, blank=False
    )
    email = models.EmailField(db_index=True, max_length=255, unique=True)
    is_active = models.BooleanField(
        _("Activate Account"),
        default=False,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()
    admin_objects = CustomAdminManager()  # manager for admin

    def __str__(self):
        return self.email


class UserBusiness(BaseModel):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name="user")
    business_name = models.CharField(max_length=50)


class UserAvailableTime(BaseModel):
    user = models.ForeignKey(
        UserAccount, on_delete=models.CASCADE, related_name="user_time"
    )
    day_of_week = models.CharField(
        max_length=10,
        choices=[
            ("Monday", "Monday"),
            ("Tuesday", "Tuesday"),
            ("Wednesday", "Wednesday"),
            ("Thursday", "Thursday"),
            ("Friday", "Friday"),
            ("Saturday", "Saturday"),
            ("Sunday", "Sunday"),
        ],
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    # True if multiple participants can book on session
    is_group_available = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "day_of_week", "start_time", "end_time"],
                name="unique_user_time",
            )
        ]


class UserAppointment(BaseModel):
    message = models.TextField(null=True, blank=True)  # message to service_provider
    name = models.CharField(max_length=50, validators=[validate_name])
    email = models.EmailField(db_index=True, max_length=255, unique=True)
    phone_number = models.CharField(
        max_length=20,
        validators=[validate_phone_number],
        blank=True,
        null=True,
    )
    session_time = models.ForeignKey(
        UserAvailableTime,
        on_delete=models.SET_NULL,
        related_name="user_session",
        null=True,
    )


class Annotation(BaseModel):
    id = models.CharField(primary_key=True, max_length=10)
    thread_id = models.CharField(max_length=20)
    text = models.TextField()
    position = models.CharField(max_length=255)
    user_email = models.EmailField(
        db_index=True, max_length=255
    )  # not authenticating user
    annotation_label = models.CharField(max_length=15, choices=ANNOTATION)

    def save(self, *args, **kwargs):
        if self._state.adding:
            max_retries = 3
            for _ in range(max_retries):
                try:
                    with transaction.atomic():
                        self.id = self.generate_key()
                        return super().save(*args, **kwargs)
                except IntegrityError:  # for unique constraint cases
                    continue
            raise IntegrityError(
                "Unable to generate a unique key after multiple retries"
            )
        return super().save(*args, **kwargs)

    def generate_key(self) -> str:
        """
        Generates a random base58-encoded string of length 8.

        Returns:
            str: A random base58-encoded string of length 8.
        """
        base58_id = base58.b58encode(uuid.uuid4().bytes[:10]).decode("utf-8")
        return base58_id[:8]

    def __str__(self) -> str:
        return self.id


class AnnotationComment(BaseModel):
    text = models.TextField()
    author_email = models.EmailField(db_index=True, max_length=255)
    annotation = models.ForeignKey(Annotation, on_delete=models.CASCADE)
