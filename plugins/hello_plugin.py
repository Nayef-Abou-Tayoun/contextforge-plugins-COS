# -*- coding: utf-8 -*-
"""Simple Hello Plugin for Bootcamp Demo

Copyright 2026
SPDX-License-Identifier: Apache-2.0

A simple plugin that logs friendly greetings before and after tool execution.
Perfect for demonstrating dynamic plugin loading from COS!
"""

import logging
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


class HelloPlugin(Plugin):
    """A friendly plugin that greets users during tool execution.
    
    This is a simple, functional plugin perfect for bootcamp demonstrations.
    It logs messages before and after each tool invocation.
    """

    def __init__(self, config: PluginConfig):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        cfg = self._config.config
        
        # Customizable greeting message
        self.greeting = cfg.get("greeting", "Hello")
        self.farewell = cfg.get("farewell", "Goodbye")
        
        # Track greeting count
        self.greeting_count = 0
        
        self.logger.info(
            f"HelloPlugin initialized - Greeting: '{self.greeting}', Farewell: '{self.farewell}'"
        )

    async def tool_pre_invoke(self, payload: ToolPreInvokePayload, context: PluginContext) -> ToolPreInvokeResult:
        """Called before a tool is invoked - log a friendly greeting."""
        self.greeting_count += 1
        
        self.logger.info(
            f"👋 {self.greeting}! About to execute tool: {payload.tool_name} "
            f"(Greeting #{self.greeting_count})"
        )
        
        return ToolPreInvokeResult(payload=payload)

    async def tool_post_invoke(self, payload: ToolPostInvokePayload, context: PluginContext) -> ToolPostInvokeResult:
        """Called after a tool is invoked - log a friendly farewell."""
        self.logger.info(
            f"👋 {self.farewell}! Finished executing tool: {payload.tool_name}"
        )
        
        # Optionally add greeting info to response metadata
        if hasattr(payload, 'metadata'):
            if payload.metadata is None:
                payload.metadata = {}
            payload.metadata['hello_plugin_greeting_count'] = self.greeting_count
        
        return ToolPostInvokeResult(payload=payload)


# Made with Bob