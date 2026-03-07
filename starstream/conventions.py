"""
Conventions module - Auto-detection helpers for StarStream
"""

import re
from typing import Dict, Any, Optional, List


class ConventionBase:
    """Base class for all conventions."""

    def detect(self, route_path: str, **kwargs) -> Optional[str]:
        """Detect and return the appropriate topic."""
        raise NotImplementedError


class AutoTopic(ConventionBase):
    """
    Auto-detect topic based on route path.

    Rules:
    - /chat -> "chat"
    - /api/chat -> "api:chat"
    - /room/{room_id} -> "room:{room_id}"
    - /user/{user_id}/dm -> "user:{user_id}"
    """

    PRIORITY_PARAMS = ["room_id", "user_id", "channel_id", "topic_id"]

    def detect(self, route_path: str, **kwargs) -> str:
        """Generate topic from route path and parameters."""
        # Check for priority parameters first
        for param in self.PRIORITY_PARAMS:
            if param in kwargs:
                value = kwargs[param]
                # Remove _id suffix for cleaner topics
                topic_type = param.replace("_id", "")
                return f"{topic_type}:{value}"

        # Clean path: remove {params} and normalize
        path = re.sub(r"\{[^}]+\}", "", route_path)
        parts = [p for p in path.split("/") if p]

        return ":".join(parts) if parts else "global"

    @staticmethod
    def from_route(route_path: str, **kwargs) -> str:
        """Static helper to generate topic."""
        return AutoTopic().detect(route_path, **kwargs)


class AutoRoom(ConventionBase):
    """
    Auto-detect room based on parameters.

    Rules:
    - room_id=123 -> "room:123"
    - room_name=general -> "room:general"
    """

    ROOM_PARAMS = ["room_id", "room_name", "room", "channel", "channel_id"]

    def detect(self, route_path: str, **kwargs) -> Optional[str]:
        """Detect room from kwargs."""
        for param in self.ROOM_PARAMS:
            if param in kwargs:
                return f"room:{kwargs[param]}"

        # Try to extract from route path
        match = re.search(r"room[s]?/([a-zA-Z0-9_-]+)", route_path)
        if match:
            return f"room:{match.group(1)}"

        return None

    @staticmethod
    def from_kwargs(**kwargs) -> Optional[str]:
        """Static helper to get room from kwargs."""
        for param in AutoRoom.ROOM_PARAMS:
            if param in kwargs:
                return f"room:{kwargs[param]}"
        return None

    @staticmethod
    def from_kwargs(**kwargs) -> Optional[str]:
        """Static helper to get room from kwargs."""
        for param in AutoRoom.ROOM_PARAMS:
            if param in kwargs:
                return f"room:{kwargs[param]}"
        return None


class AutoUser(ConventionBase):
    """
    Auto-detect user for direct messaging.

    Rules:
    - user_id=456 -> "user:456"
    - username=john -> "user:john"
    """

    USER_PARAMS = ["user_id", "username", "user", "to_user", "recipient"]

    def detect(self, route_path: str, **kwargs) -> Optional[str]:
        """Detect user from kwargs."""
        for param in self.USER_PARAMS:
            if param in kwargs:
                return f"user:{kwargs[param]}"

        # Try to extract from route path
        match = re.search(r"user[s]?/(\w+)", route_path)
        if match:
            return f"user:{match.group(1)}"

        return None

    @staticmethod
    def from_kwargs(**kwargs) -> Optional[str]:
        """Static helper to get user from kwargs."""
        for param in AutoUser.USER_PARAMS:
            if param in kwargs:
                return f"user:{kwargs[param]}"
        return None


class ConventionRegistry:
    """
    Registry of conventions with priority order.
    """

    def __init__(self):
        self.conventions: List[ConventionBase] = [
            AutoRoom(),
            AutoUser(),
            AutoTopic(),
        ]

    def detect_topic(self, route_path: str, **kwargs) -> str:
        """
        Apply conventions in priority order.
        First match wins.
        """
        for convention in self.conventions:
            result = convention.detect(route_path, **kwargs)
            if result:
                return result

        return "global"


# Predefined convention patterns for common use cases


class ChatConvention(ConventionBase):
    """Convention for chat applications."""

    def detect(self, route_path: str, **kwargs) -> str:
        if "room_id" in kwargs:
            return f"chat:room:{kwargs['room_id']}"

        # Try to extract room from path like /room/general or /rooms/general
        match = re.search(r"room[s]?/([a-zA-Z0-9_-]+)", route_path)
        if match:
            return f"chat:room:{match.group(1)}"

        if "user_id" in kwargs:
            return f"chat:dm:{kwargs['user_id']}"

        # Try to extract DM from path like /dm/john or /dms/john
        match = re.search(r"dm[s]?/([a-zA-Z0-9_-]+)", route_path)
        if match:
            return f"chat:dm:{match.group(1)}"

        return "chat:global"


class GameConvention(ConventionBase):
    """Convention for game/multiplayer applications."""

    def detect(self, route_path: str, **kwargs) -> str:
        # First check kwargs
        if "game_id" in kwargs:
            return f"game:{kwargs['game_id']}"
        if "match_id" in kwargs:
            return f"game:{kwargs['match_id']}"

        # Try to extract match from path like /match/abc123
        match = re.search(r"match/([a-zA-Z0-9_-]+)", route_path)
        if match:
            return f"game:{match.group(1)}"

        if "lobby_id" in kwargs:
            return f"game:lobby:{kwargs['lobby_id']}"

        # Try to extract lobby from path like /lobby/europe
        match = re.search(r"lobby/([a-zA-Z0-9_-]+)", route_path)
        if match:
            return f"game:lobby:{match.group(1)}"

        return "game:lobby"


class DocumentConvention(ConventionBase):
    """Convention for collaborative document editing."""

    def detect(self, route_path: str, **kwargs) -> str:
        doc_id = kwargs.get("doc_id") or kwargs.get("document_id")
        if doc_id:
            return f"doc:{doc_id}"

        return "doc:default"
