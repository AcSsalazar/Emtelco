from rest_framework import generics, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.utils import get_customer
from apps.agent.llm.base import LLMProviderError
from apps.agent.orchestrator import run_agent

from .models import Conversation, Message
from .serializers import (
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
)

DEFAULT_TITLE = "Nueva conversación"


class CustomerConversationMixin:
    def get_queryset(self):
        customer = get_customer(self.request.user)
        if customer is None:
            return Conversation.objects.none()
        return Conversation.objects.filter(customer=customer)

    def get_conversation(self, pk: int) -> Conversation:
        return get_object_or_404(self.get_queryset(), pk=pk)


class ConversationListView(CustomerConversationMixin, generics.ListCreateAPIView):
    serializer_class = ConversationSerializer

    def perform_create(self, serializer):
        customer = get_customer(self.request.user)
        serializer.save(
            customer=customer,
            title=serializer.validated_data.get("title") or DEFAULT_TITLE,
        )


class ConversationDetailView(CustomerConversationMixin, generics.RetrieveAPIView):
    serializer_class = ConversationDetailSerializer


class ConversationMessagesView(CustomerConversationMixin, APIView):
    def get(self, request, pk):
        conversation = self.get_conversation(pk)
        messages = conversation.messages.exclude(role=Message.Role.TOOL)
        return Response(MessageSerializer(messages, many=True).data)

    def post(self, request, pk):
        conversation = self.get_conversation(pk)

        # Recover an interrupted turn: regenerate the reply for the last user
        # message without duplicating it.
        if request.data.get("retry"):
            return self._retry(conversation)

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data["content"]
        self._maybe_set_title(conversation, content)
        return self._run(conversation, content, persist_user_message=True)

    def _run(self, conversation, content, persist_user_message):
        try:
            result = run_agent(
                conversation, content, persist_user_message=persist_user_message
            )
        except LLMProviderError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        return Response({"reply": result.reply, "escalated": result.escalated})

    def _retry(self, conversation):
        last = (
            conversation.messages.exclude(role=Message.Role.TOOL)
            .order_by("-id")
            .first()
        )
        if last is None:
            return Response(
                {"detail": "No hay mensajes para reintentar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if last.role == Message.Role.ASSISTANT:
            return Response(
                {
                    "reply": last.content,
                    "escalated": conversation.escalated,
                    "already_answered": True,
                }
            )
        return self._run(conversation, last.content, persist_user_message=False)

    @staticmethod
    def _maybe_set_title(conversation: Conversation, content: str) -> None:
        if conversation.messages.filter(role=Message.Role.USER).exists():
            return
        if conversation.title and conversation.title != DEFAULT_TITLE:
            return
        title = " ".join(content.split())[:60]
        if title:
            conversation.title = title
            conversation.save(update_fields=["title", "updated_at"])
