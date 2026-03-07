"""
Unit tests for convention detection (auto-topic, auto-room, auto-user).
"""

import pytest
from starstream.conventions import (
    AutoTopic,
    AutoRoom,
    AutoUser,
    ConventionRegistry,
    ChatConvention,
    GameConvention,
)


class TestAutoTopic:
    """Test auto-topic detection from routes."""

    def test_auto_topic_from_simple_route(self):
        """Simple route → topic name."""
        convention = AutoTopic()
        assert convention.detect("/chat") == "chat"
        assert convention.detect("/notifications") == "notifications"

    def test_auto_topic_from_nested_route(self):
        """Nested route → namespaced topic."""
        convention = AutoTopic()
        assert convention.detect("/api/chat") == "api:chat"
        assert convention.detect("/v1/notifications") == "v1:notifications"
        assert convention.detect("/api/v2/messages") == "api:v2:messages"

    def test_auto_topic_ignores_params(self):
        """Route params are cleaned from topic."""
        convention = AutoTopic()
        assert convention.detect("/room/{room_id}") == "room"
        assert convention.detect("/user/{user_id}/profile") == "user:profile"

    def test_auto_topic_from_kwargs_room_id(self):
        """room_id parameter takes priority."""
        convention = AutoTopic()
        assert convention.detect("/any-path", room_id="123") == "room:123"
        assert convention.detect("/room/{id}", room_id="456") == "room:456"

    def test_auto_topic_from_kwargs_user_id(self):
        """user_id parameter takes priority."""
        convention = AutoTopic()
        assert convention.detect("/any-path", user_id="789") == "user:789"

    def test_auto_topic_from_kwargs_channel_id(self):
        """channel_id parameter works."""
        convention = AutoTopic()
        assert convention.detect("/chat", channel_id="general") == "channel:general"

    def test_auto_topic_priority_order(self):
        """Priority: room_id > user_id > channel_id > path."""
        convention = AutoTopic()

        # Room has highest priority
        assert convention.detect("/chat", room_id="1", user_id="2") == "room:1"

        # User has priority over channel
        assert convention.detect("/chat", user_id="2", channel_id="3") == "user:2"

        # Channel has priority over path
        assert convention.detect("/chat", channel_id="3") == "channel:3"

    def test_auto_topic_default_fallback(self):
        """Empty path defaults to 'global'."""
        convention = AutoTopic()
        assert convention.detect("") == "global"
        assert convention.detect("/") == "global"

    def test_auto_topic_static_helper(self):
        """Static helper method works."""
        assert AutoTopic.from_route("/chat") == "chat"
        assert AutoTopic.from_route("/room/{id}", room_id="123") == "room:123"


class TestAutoRoom:
    """Test auto-room detection."""

    def test_auto_room_from_room_id(self):
        """room_id → room:topic."""
        convention = AutoRoom()
        assert convention.detect("/any", room_id="123") == "room:123"

    def test_auto_room_from_room_name(self):
        """room_name → room:topic."""
        convention = AutoRoom()
        assert convention.detect("/any", room_name="general") == "room:general"

    def test_auto_room_from_path(self):
        """Extract room from path."""
        convention = AutoRoom()
        assert convention.detect("/rooms/general") == "room:general"
        assert convention.detect("/room/tech-talk") == "room:tech-talk"

    def test_auto_room_none_when_no_match(self):
        """Returns None when no room detected."""
        convention = AutoRoom()
        assert convention.detect("/chat") is None
        assert convention.detect("/user/profile") is None

    def test_auto_room_static_helper(self):
        """Static helper method works."""
        assert AutoRoom.from_kwargs(room_id="123") == "room:123"
        assert AutoRoom.from_kwargs(user_id="456") is None


class TestAutoUser:
    """Test auto-user detection for DMs."""

    def test_auto_user_from_user_id(self):
        """user_id → user:topic."""
        convention = AutoUser()
        assert convention.detect("/any", user_id="456") == "user:456"

    def test_auto_user_from_username(self):
        """username → user:topic."""
        convention = AutoUser()
        assert convention.detect("/any", username="john") == "user:john"

    def test_auto_user_from_path(self):
        """Extract user from path."""
        convention = AutoUser()
        assert convention.detect("/users/john/dm") == "user:john"
        assert convention.detect("/user/jane/profile") == "user:jane"

    def test_auto_user_none_when_no_match(self):
        """Returns None when no user detected."""
        convention = AutoUser()
        assert convention.detect("/chat") is None

    def test_auto_user_static_helper(self):
        """Static helper method works."""
        assert AutoUser.from_kwargs(user_id="789") == "user:789"
        assert AutoUser.from_kwargs(room_id="123") is None


class TestConventionRegistry:
    """Test registry that applies conventions in priority order."""

    def test_registry_priority_order(self):
        """First matching convention wins."""
        registry = ConventionRegistry()

        # Room should win over path
        assert registry.detect_topic("/chat", room_id="123") == "room:123"

        # User should win over path
        assert registry.detect_topic("/chat", user_id="456") == "user:456"

        # Path is last resort
        assert registry.detect_topic("/notifications") == "notifications"

    def test_registry_default_global(self):
        """Defaults to 'global'."""
        registry = ConventionRegistry()
        assert registry.detect_topic("/") == "global"
        assert registry.detect_topic("") == "global"


class TestChatConvention:
    """Test chat-specific convention."""

    def test_chat_room_detection(self):
        """Detect chat rooms."""
        convention = ChatConvention()
        assert convention.detect("/room/general") == "chat:room:general"
        assert convention.detect("/chat", room_id="123") == "chat:room:123"

    def test_chat_dm_detection(self):
        """Detect DMs."""
        convention = ChatConvention()
        assert convention.detect("/dm/john") == "chat:dm:john"
        assert convention.detect("/chat", user_id="456") == "chat:dm:456"

    def test_chat_global_fallback(self):
        """Default to global chat."""
        convention = ChatConvention()
        assert convention.detect("/chat") == "chat:global"


class TestGameConvention:
    """Test game-specific convention."""

    def test_game_match_detection(self):
        """Detect game matches."""
        convention = GameConvention()
        assert convention.detect("/match/abc123") == "game:abc123"
        assert convention.detect("/play", game_id="xyz789") == "game:xyz789"

    def test_game_lobby_detection(self):
        """Detect game lobbies."""
        convention = GameConvention()
        assert convention.detect("/lobby/europe") == "game:lobby:europe"
        assert convention.detect("/play", lobby_id="pro") == "game:lobby:pro"

    def test_game_lobby_fallback(self):
        """Default to main lobby."""
        convention = GameConvention()
        assert convention.detect("/play") == "game:lobby"
