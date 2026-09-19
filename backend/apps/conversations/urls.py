from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListView,
    ConversationMessagesView,
)

urlpatterns = [
    path("conversations", ConversationListView.as_view(), name="conversation-list"),
    path("conversations/<int:pk>", ConversationDetailView.as_view(), name="conversation-detail"),
    path(
        "conversations/<int:pk>/messages",
        ConversationMessagesView.as_view(),
        name="conversation-messages",
    ),
]
