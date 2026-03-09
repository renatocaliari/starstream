"""
Collaborative editing module for StarStream.

This module provides CRDT-based collaborative editing capabilities
using Loro under the hood.
"""

from .engine import CollaborativeEngine

__all__ = ["CollaborativeEngine"]
