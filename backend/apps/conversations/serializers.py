from rest_framework import serializers

from .models import Conversation, Message

# Maximum number of messages returned when loading a conversation. Older
# messages remain stored; this only bounds the payload.
MESSAGE_LIMIT = 50


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "metadata", "created_at", "tool_name"]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "escalated",
            "created_at",
            "updated_at",
            "message_count",
        ]
        read_only_fields = ["id", "escalated", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.messages.exclude(role=Message.Role.TOOL).count()


class ConversationDetailSerializer(ConversationSerializer):
    messages = serializers.SerializerMethodField()

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]

    def get_messages(self, obj):
        queryset = (
            obj.messages.exclude(role=Message.Role.TOOL)
            .order_by("-created_at", "-id")[:MESSAGE_LIMIT]
        )
        return MessageSerializer(list(reversed(list(queryset))), many=True).data


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=2000, allow_blank=False)
