# -*- coding: utf-8 -*-
"""Simple Tool Cost Tracker Plugin for Bootcamp Demo

Copyright 2026
SPDX-License-Identifier: Apache-2.0

This plugin tracks the cost of each tool invocation and logs it.
Perfect for demonstrating dynamic plugin loading from COS!
"""

import logging
import time
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


class ToolCostTrackerPlugin(Plugin):
    """Tracks and logs the cost of each tool invocation.
    
    This is a simple, functional plugin perfect for bootcamp demonstrations.
    It calculates costs based on configurable rates per tool.
    """

    def __init__(self, config: PluginConfig):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        cfg = self._config.config
        
        # Default cost rates (in cents per call)
        self.default_cost = cfg.get("default_cost_per_call", 0.01)
        
        # Custom costs for specific tools
        self.tool_costs = cfg.get("tool_costs", {
            "expensive_tool": 0.10,
            "cheap_tool": 0.001,
        })
        
        # Track total costs
        self.total_cost = 0.0
        self.call_count = 0
        
        self.logger.info(
            f"ToolCostTrackerPlugin initialized - "
            f"Default cost: ${self.default_cost:.4f} per call"
        )

    async def tool_pre_invoke(self, payload: ToolPreInvokePayload, context: PluginContext) -> ToolPreInvokeResult:
        """Called before a tool is invoked - record start time."""
        # Store start time in metadata for duration calculation
        if not hasattr(payload, '_cost_tracker_start'):
            payload._cost_tracker_start = time.time()
        
        return ToolPreInvokeResult(payload=payload)

    async def tool_post_invoke(self, payload: ToolPostInvokePayload, context: PluginContext) -> ToolPostInvokeResult:
        """Called after a tool is invoked - calculate and log cost."""
        tool_name = payload.tool_name
        
        # Calculate duration if we have start time
        duration = 0.0
        if hasattr(payload, '_cost_tracker_start'):
            duration = time.time() - payload._cost_tracker_start
        
        # Get cost for this tool
        cost = self.tool_costs.get(tool_name, self.default_cost)
        
        # Update totals
        self.total_cost += cost
        self.call_count += 1
        
        # Log the cost
        self.logger.info(
            f"💰 Tool Cost: {tool_name} - "
            f"${cost:.4f} (duration: {duration:.2f}s) | "
            f"Total: ${self.total_cost:.4f} ({self.call_count} calls)"
        )
        
        # Optionally add cost info to response metadata
        if hasattr(payload, 'metadata'):
            if payload.metadata is None:
                payload.metadata = {}
            payload.metadata['cost'] = cost
            payload.metadata['total_cost'] = self.total_cost
            payload.metadata['call_count'] = self.call_count
        
        return ToolPostInvokeResult(payload=payload)

# Made with Bob
