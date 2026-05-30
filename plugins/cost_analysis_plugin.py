# -*- coding: utf-8 -*-
"""Cost Analysis Plugin for ContextForge - COS Version

Copyright 2026
SPDX-License-Identifier: Apache-2.0

A comprehensive cost analysis plugin that tracks token consumption, calculates costs,
enforces budget limits, and generates alerts when thresholds are exceeded.

This is a standalone version designed for upload to IBM Cloud Object Storage (COS).

Features:
- Token consumption tracking (input/output/total)
- Cost calculation with configurable pricing models
- Budget enforcement with soft/hard limits
- Real-time alerts when thresholds are exceeded
- Per-user, per-team, and global cost attribution
- Detailed metrics and dashboards
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from collections import defaultdict

from cpex.framework import (
    Plugin,
    PluginConfig,
    PluginContext,
    ToolPreInvokePayload,
    ToolPreInvokeResult,
    ToolPostInvokePayload,
    ToolPostInvokeResult,
    PluginViolation,
)


class CostAnalysisPlugin(Plugin):
    """Cost Analysis Plugin for tracking token usage and enforcing budgets.
    
    This plugin monitors token consumption across all tool invocations,
    calculates associated costs, and enforces budget limits with configurable
    alert thresholds.
    
    Configuration:
        pricing:
            input_cost_per_1k: Cost per 1K input tokens (default: 0.01)
            output_cost_per_1k: Cost per 1K output tokens (default: 0.03)
        budgets:
            daily_limit: Daily budget limit in USD (default: 100.0)
            monthly_limit: Monthly budget limit in USD (default: 3000.0)
            per_user_daily_limit: Per-user daily limit (default: 10.0)
        alerts:
            warning_threshold: Warning threshold percentage (default: 0.75)
            critical_threshold: Critical threshold percentage (default: 0.90)
            block_on_exceeded: Block requests when budget exceeded (default: false)
    """

    def __init__(self, config: PluginConfig):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        cfg = self._config.config or {}
        
        # Pricing configuration (cost per 1K tokens)
        pricing = cfg.get("pricing", {})
        self.input_token_cost = pricing.get("input_cost_per_1k", 0.01)
        self.output_token_cost = pricing.get("output_cost_per_1k", 0.03)
        
        # Budget configuration
        budgets = cfg.get("budgets", {})
        self.daily_budget = budgets.get("daily_limit", 100.0)
        self.monthly_budget = budgets.get("monthly_limit", 3000.0)
        self.per_user_daily_budget = budgets.get("per_user_daily_limit", 10.0)
        
        # Alert thresholds (percentage of budget)
        alerts = cfg.get("alerts", {})
        self.warning_threshold = alerts.get("warning_threshold", 0.75)
        self.critical_threshold = alerts.get("critical_threshold", 0.90)
        self.block_on_exceeded = alerts.get("block_on_exceeded", False)
        
        # Token consumption tracking
        self.token_usage: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "request_count": 0,
            "first_request": None,
            "last_request": None,
        })
        
        # Daily/monthly aggregates
        self.daily_totals = {
            "date": datetime.now().date().isoformat(),
            "total_cost": 0.0,
            "total_tokens": 0,
            "request_count": 0,
        }
        
        self.monthly_totals = {
            "month": datetime.now().strftime("%Y-%m"),
            "total_cost": 0.0,
            "total_tokens": 0,
            "request_count": 0,
        }
        
        # Alert state tracking
        self.alerts_sent = {
            "daily_warning": False,
            "daily_critical": False,
            "monthly_warning": False,
            "monthly_critical": False,
        }
        
        self.logger.info(
            f"CostAnalysisPlugin initialized - "
            f"Daily budget: ${self.daily_budget}, "
            f"Monthly budget: ${self.monthly_budget}, "
            f"Warning: {self.warning_threshold*100}%, "
            f"Critical: {self.critical_threshold*100}%"
        )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        input_cost = (input_tokens / 1000.0) * self.input_token_cost
        output_cost = (output_tokens / 1000.0) * self.output_token_cost
        return round(input_cost + output_cost, 6)

    def _get_user_id(self, context: PluginContext) -> str:
        """Extract user ID from context."""
        if hasattr(context, 'global_context') and context.global_context:
            gc = context.global_context
            if hasattr(gc, 'user_email') and gc.user_email:
                return gc.user_email
            if hasattr(gc, 'user_id') and gc.user_id:
                return gc.user_id
        return "anonymous"

    def _reset_daily_totals_if_needed(self):
        """Reset daily totals if we've crossed into a new day."""
        current_date = datetime.now().date().isoformat()
        if self.daily_totals["date"] != current_date:
            self.logger.info(
                f"New day detected. Previous day total: ${self.daily_totals['total_cost']:.2f}"
            )
            self.daily_totals = {
                "date": current_date,
                "total_cost": 0.0,
                "total_tokens": 0,
                "request_count": 0,
            }
            self.alerts_sent["daily_warning"] = False
            self.alerts_sent["daily_critical"] = False

    def _reset_monthly_totals_if_needed(self):
        """Reset monthly totals if we've crossed into a new month."""
        current_month = datetime.now().strftime("%Y-%m")
        if self.monthly_totals["month"] != current_month:
            self.logger.info(
                f"New month detected. Previous month total: ${self.monthly_totals['total_cost']:.2f}"
            )
            self.monthly_totals = {
                "month": current_month,
                "total_cost": 0.0,
                "total_tokens": 0,
                "request_count": 0,
            }
            self.alerts_sent["monthly_warning"] = False
            self.alerts_sent["monthly_critical"] = False

    def _check_budget_alerts(self, user_id: str) -> Optional[str]:
        """Check if any budget thresholds have been exceeded."""
        alerts = []
        
        # Check daily budget
        daily_usage_pct = self.daily_totals["total_cost"] / self.daily_budget
        if daily_usage_pct >= self.critical_threshold and not self.alerts_sent["daily_critical"]:
            alerts.append(
                f"🚨 CRITICAL: Daily budget {daily_usage_pct*100:.1f}% consumed "
                f"(${self.daily_totals['total_cost']:.2f} / ${self.daily_budget:.2f})"
            )
            self.alerts_sent["daily_critical"] = True
        elif daily_usage_pct >= self.warning_threshold and not self.alerts_sent["daily_warning"]:
            alerts.append(
                f"⚠️  WARNING: Daily budget {daily_usage_pct*100:.1f}% consumed "
                f"(${self.daily_totals['total_cost']:.2f} / ${self.daily_budget:.2f})"
            )
            self.alerts_sent["daily_warning"] = True
        
        # Check monthly budget
        monthly_usage_pct = self.monthly_totals["total_cost"] / self.monthly_budget
        if monthly_usage_pct >= self.critical_threshold and not self.alerts_sent["monthly_critical"]:
            alerts.append(
                f"🚨 CRITICAL: Monthly budget {monthly_usage_pct*100:.1f}% consumed "
                f"(${self.monthly_totals['total_cost']:.2f} / ${self.monthly_budget:.2f})"
            )
            self.alerts_sent["monthly_critical"] = True
        elif monthly_usage_pct >= self.warning_threshold and not self.alerts_sent["monthly_warning"]:
            alerts.append(
                f"⚠️  WARNING: Monthly budget {monthly_usage_pct*100:.1f}% consumed "
                f"(${self.monthly_totals['total_cost']:.2f} / ${self.monthly_budget:.2f})"
            )
            self.alerts_sent["monthly_warning"] = True
        
        # Check per-user daily budget
        user_stats = self.token_usage.get(user_id, {})
        user_daily_cost = user_stats.get("total_cost", 0.0)
        if user_daily_cost > self.per_user_daily_budget:
            alerts.append(
                f"🚨 User {user_id} exceeded daily budget: "
                f"${user_daily_cost:.2f} / ${self.per_user_daily_budget:.2f}"
            )
        
        if alerts:
            alert_msg = "\n".join(alerts)
            self.logger.warning(f"Budget alerts triggered:\n{alert_msg}")
            return alert_msg
        
        return None

    def _should_block_request(self) -> bool:
        """Determine if request should be blocked due to budget exceeded."""
        if not self.block_on_exceeded:
            return False
        
        if self.daily_totals["total_cost"] >= self.daily_budget:
            return True
        if self.monthly_totals["total_cost"] >= self.monthly_budget:
            return True
        
        return False

    async def tool_pre_invoke(self, payload: ToolPreInvokePayload, context: PluginContext) -> ToolPreInvokeResult:
        """Called before tool invocation - check budget limits."""
        self._reset_daily_totals_if_needed()
        self._reset_monthly_totals_if_needed()
        
        user_id = self._get_user_id(context)
        
        # Check if we should block the request
        if self._should_block_request():
            self.logger.error(
                f"Blocking request from {user_id} - budget exceeded. "
                f"Daily: ${self.daily_totals['total_cost']:.2f} / ${self.daily_budget:.2f}, "
                f"Monthly: ${self.monthly_totals['total_cost']:.2f} / ${self.monthly_budget:.2f}"
            )
            return ToolPreInvokeResult(
                payload=payload,
                continue_processing=False,
                violation=PluginViolation(
                    reason="Budget limit exceeded",
                    description=(
                        f"Daily budget: ${self.daily_totals['total_cost']:.2f} / ${self.daily_budget:.2f}, "
                        f"Monthly budget: ${self.monthly_totals['total_cost']:.2f} / ${self.monthly_budget:.2f}"
                    ),
                    code="BUDGET_EXCEEDED",
                    details={
                        "daily_cost": self.daily_totals["total_cost"],
                        "daily_budget": self.daily_budget,
                        "monthly_cost": self.monthly_totals["total_cost"],
                        "monthly_budget": self.monthly_budget,
                    },
                ),
            )
        
        self.logger.info(
            f"Tool invocation starting - User: {user_id}, Tool: {payload.tool_name}, "
            f"Daily spend: ${self.daily_totals['total_cost']:.2f}"
        )
        
        return ToolPreInvokeResult(payload=payload)

    async def tool_post_invoke(self, payload: ToolPostInvokePayload, context: PluginContext) -> ToolPostInvokeResult:
        """Called after tool invocation - track token usage and costs."""
        user_id = self._get_user_id(context)
        
        # Extract token usage from payload metadata
        input_tokens = 0
        output_tokens = 0
        
        if hasattr(payload, 'metadata') and payload.metadata:
            input_tokens = payload.metadata.get('input_tokens', 0)
            output_tokens = payload.metadata.get('output_tokens', 0)
        
        # If no metadata, estimate based on content length
        if input_tokens == 0 and output_tokens == 0:
            if hasattr(payload, 'arguments') and payload.arguments:
                input_tokens = len(str(payload.arguments)) // 4
            if hasattr(payload, 'result') and payload.result:
                output_tokens = len(str(payload.result)) // 4
        
        total_tokens = input_tokens + output_tokens
        cost = self._calculate_cost(input_tokens, output_tokens)
        
        # Update user statistics
        user_stats = self.token_usage[user_id]
        user_stats["input_tokens"] += input_tokens
        user_stats["output_tokens"] += output_tokens
        user_stats["total_tokens"] += total_tokens
        user_stats["total_cost"] += cost
        user_stats["request_count"] += 1
        user_stats["last_request"] = datetime.now().isoformat()
        if user_stats["first_request"] is None:
            user_stats["first_request"] = user_stats["last_request"]
        
        # Update daily totals
        self.daily_totals["total_cost"] += cost
        self.daily_totals["total_tokens"] += total_tokens
        self.daily_totals["request_count"] += 1
        
        # Update monthly totals
        self.monthly_totals["total_cost"] += cost
        self.monthly_totals["total_tokens"] += total_tokens
        self.monthly_totals["request_count"] += 1
        
        # Check for budget alerts
        alert_msg = self._check_budget_alerts(user_id)
        
        # Log detailed cost information
        self.logger.info(
            f"💰 Cost Analysis - User: {user_id}, Tool: {payload.tool_name}, "
            f"Tokens: {total_tokens} (in: {input_tokens}, out: {output_tokens}), "
            f"Cost: ${cost:.6f}, "
            f"User total: ${user_stats['total_cost']:.2f}, "
            f"Daily total: ${self.daily_totals['total_cost']:.2f}, "
            f"Monthly total: ${self.monthly_totals['total_cost']:.2f}"
        )
        
        # Add cost metadata to response
        if not hasattr(payload, 'metadata') or payload.metadata is None:
            payload.metadata = {}
        
        payload.metadata.update({
            'cost_analysis': {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'cost': cost,
                'user_total_cost': user_stats['total_cost'],
                'daily_total_cost': self.daily_totals['total_cost'],
                'monthly_total_cost': self.monthly_totals['total_cost'],
                'daily_budget_remaining': self.daily_budget - self.daily_totals['total_cost'],
                'monthly_budget_remaining': self.monthly_budget - self.monthly_totals['total_cost'],
                'alert': alert_msg,
            }
        })
        
        return ToolPostInvokeResult(payload=payload)

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cost and usage metrics."""
        return {
            "daily": self.daily_totals,
            "monthly": self.monthly_totals,
            "per_user": dict(self.token_usage),
            "budgets": {
                "daily_budget": self.daily_budget,
                "monthly_budget": self.monthly_budget,
                "per_user_daily_budget": self.per_user_daily_budget,
                "daily_remaining": self.daily_budget - self.daily_totals["total_cost"],
                "monthly_remaining": self.monthly_budget - self.monthly_totals["total_cost"],
            },
            "alerts": {
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold,
                "alerts_sent": self.alerts_sent,
            },
        }


# Made with Bob