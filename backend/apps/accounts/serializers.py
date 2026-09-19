from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Customer, CustomerModeration, CustomerProfile
from .validators import validate_full_name, validate_identification, validate_phone

User = get_user_model()


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "identification", "full_name", "phone", "email", "created_at"]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "customer"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    """Register a new user.

    If the identification matches a seeded customer that has no user account
    yet, the existing profile is claimed instead of duplicated. This supports
    the "returning customer" flow from the specification.
    """

    identification = serializers.CharField(max_length=11)
    full_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=10)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_full_name(self, value):
        try:
            validate_full_name(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value.strip()

    def validate_phone(self, value):
        try:
            validate_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Este correo ya está registrado.")
        return value

    def validate(self, attrs):
        identification = attrs["identification"]
        try:
            validate_identification(identification)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"identification": exc.messages})

        existing = Customer.objects.filter(identification=identification).first()
        if existing and existing.user_id:
            raise serializers.ValidationError(
                {"identification": "Esta identificación ya está registrada."}
            )

        email_conflict = Customer.objects.filter(email__iexact=attrs["email"])
        if existing:
            email_conflict = email_conflict.exclude(pk=existing.pk)
        if email_conflict.exists():
            raise serializers.ValidationError({"email": "Este correo ya está registrado."})

        attrs["_existing_customer"] = existing
        return attrs

    def create(self, validated_data):
        existing = validated_data.pop("_existing_customer", None)
        password = validated_data.pop("password")
        email = validated_data["email"]
        full_name = validated_data["full_name"]

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name.split(" ")[0],
        )

        if existing:
            existing.user = user
            existing.full_name = full_name
            existing.phone = validated_data["phone"]
            existing.email = email
            existing.save()
            customer = existing
        else:
            customer = Customer.objects.create(user=user, **validated_data)

        CustomerModeration.objects.get_or_create(customer=customer)
        return user


class CustomerProfileSerializer(serializers.ModelSerializer):
    os_label = serializers.CharField(source="get_os_preference_display", read_only=True)
    experience_label = serializers.CharField(
        source="get_experience_level_display", read_only=True
    )

    class Meta:
        model = CustomerProfile
        fields = [
            "use_cases",
            "software",
            "preferred_brands",
            "os_preference",
            "os_label",
            "experience_level",
            "experience_label",
            "budget_min",
            "budget_max",
            "notes",
            "updated_at",
        ]
        read_only_fields = ["updated_at", "os_label", "experience_label"]


class LoginSerializer(serializers.Serializer):
    # ``identifier`` accepts an email or a customer identification. ``email`` is
    # kept for backwards compatibility with earlier clients.
    identifier = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = (attrs.get("identifier") or attrs.get("email") or "").strip()
        if not identifier:
            raise serializers.ValidationError(
                {"identifier": "Ingresa tu correo o tu identificación."}
            )
        user = authenticate(
            request=self.context.get("request"),
            username=self._resolve_username(identifier),
            password=attrs["password"],
        )
        if user is None or not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Correo o identificación y contraseña incorrectos."}
            )
        refresh = RefreshToken.for_user(user)
        attrs["tokens"] = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
        attrs["user"] = user
        return attrs

    @staticmethod
    def _resolve_username(identifier: str) -> str:
        """Resolve an email or an identification to the auth username."""
        if "@" in identifier:
            return identifier.lower()
        customer = (
            Customer.objects.filter(identification=identifier)
            .select_related("user")
            .first()
        )
        if customer and customer.user_id:
            return customer.user.username
        return identifier
