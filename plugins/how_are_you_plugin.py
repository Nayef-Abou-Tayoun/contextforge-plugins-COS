# -*- coding: utf-8 -*-
"""How Are You Doing Plugin for Bootcamp Demo

Copyright 2026
SPDX-License-Identifier: Apache-2.0

A conversational plugin that adds friendly greetings and encouragement
to tool interactions. Perfect for demonstrating dynamic plugin loading from COS!
"""

import logging
import random
from typing import Dict, Any

from cpex.framework import (
    Plugin,
    PluginConfig,
    PluginContext,
    ToolPreInvokePayload,
    ToolPreInvokeResult,
    ToolPostInvokePayload,
    ToolPostInvokeResult,
)


class HowAreYouDoingPlugin(Plugin):
    """A conversational plugin that adds friendly interactions.
    
    This plugin adds variety to tool interactions with random greetings
    and encouraging messages. Perfect for bootcamp demonstrations!
    """

    # Greeting variations
    GREETINGS = [
        "How are you doing today?",
        "Hope you're having a great day!",
        "Nice to see you!",
        "Ready to get some work done?",
        "Let's make something awesome!",
    ]
    
    # Encouragement messages
    ENCOURAGEMENTS = [
        "Great job!",
        "You're doing awesome!",
        "Keep up the good work!",
        "Excellent!",
        "That was smooth!",
    ]

    def __init__(self, config: PluginConfig):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        cfg = self._config.config
        
        # Enable/disable features
        self.show_greetings = cfg.get("show_greetings", True)
        self.show_encouragement = cfg.get("show_encouragement", True)
        
        # Track interaction count
        self.interaction_count = 0
        
        self.logger.info(
            f"HowAreYouDoingPlugin initialized - "
            f"Greetings: {self.show_greetings}, Encouragement: {self.show_encouragement}"
        )

    async def tool_pre_invoke(self, payload: ToolPreInvokePayload, context: PluginContext) -> ToolPreInvokeResult:
        """Add a friendly greeting before tool execution."""
        self.interaction_count += 1
        
        if self.show_greetings:
            greeting = random.choice(self.GREETINGS)
            self.logger.info(
                f"💬 {greeting} Executing tool: {payload.tool_name} "
                f"(Interaction #{self.interaction_count})"
            )
        
        return ToolPreInvokeResult(payload=payload)

    async def tool_post_invoke(self, payload: ToolPostInvokePayload, context: PluginContext) -> ToolPostInvokeResult:
        """Add encouragement after tool execution."""
        if self.show_encouragement:
            encouragement = random.choice(self.ENCOURAGEMENTS)
            self.logger.info(
                f"💬 {encouragement} Tool '{payload.tool_name}' completed successfully!"
            )
        
        # Add interaction info to response metadata
        if hasattr(payload, 'metadata'):
            if payload.metadata is None:
                payload.metadata = {}
            payload.metadata['how_are_you_interaction_count'] = self.interaction_count
        
        return ToolPostInvokeResult(payload=payload)


# Made with Bob