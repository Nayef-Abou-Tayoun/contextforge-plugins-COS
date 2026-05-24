# -*- coding: utf-8 -*-
"""Custom PII Filter Plugin with MAC Address Detection

Copyright 2026
SPDX-License-Identifier: Apache-2.0
Author: Nayef Abou Tayoun

This plugin extends the base PIIFilterPlugin with additional MAC address detection capability.
"""

import re
import hashlib
from typing import Dict, Any, List, Tuple

from cpex.framework import (
    Plugin,
    PluginConfig,
    PluginContext,
    PromptPrehookPayload,
    PromptPrehookResult,
    PromptPosthookPayload,
    PromptPosthookResult,
    ToolPreInvokePayload,
    ToolPreInvokeResult,
    ToolPostInvokePayload,
    ToolPostInvokeResult,
)
from cpex_pii_filter.pii_filter import PIIFilterPlugin
from mcpgateway.services.logging_service import LoggingService

# Initialize logging
logging_service = LoggingService()
logger = logging_service.get_logger(__name__)


class NA_PIIFilterPlugin(Plugin):
    """Extended PII Filter Plugin with MAC address detection.
    
    This plugin wraps the base PIIFilterPlugin and adds detection and masking
    of MAC addresses (computer hardware addresses).
    
    Attributes:
        base_filter: The underlying PIIFilterPlugin instance
        detect_mac: Whether to detect MAC addresses
        mac_mask_strategy: How to mask detected MAC addresses
    """
    
    # MAC address regex pattern (matches formats like AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF)
    MAC_PATTERN = re.compile(
        r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b'
    )
    
    def __init__(self, config: PluginConfig):
        """Initialize the NA_PIIFilterPlugin.
        
        Args:
            config: Plugin configuration including detect_computer_mac setting
        """
        super().__init__(config)
        
        # Initialize the base PII filter with the same config
        self.base_filter = PIIFilterPlugin(config)
        
        # Get MAC-specific configuration
        self.detect_mac = config.config.get("detect_computer_mac", False)
        self.mac_mask_strategy = config.config.get("mac_mask_strategy", "partial")
        
        logger.info(
            "NA_PIIFilterPlugin initialized (MAC detection: %s, strategy: %s)",
            self.detect_mac,
            self.mac_mask_strategy
        )
    
    def _detect_and_mask_mac(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Detect and mask MAC addresses in text.
        
        Args:
            text: The text to scan for MAC addresses
            
        Returns:
            Tuple of (masked_text, list of detections)
        """
        if not self.detect_mac or not text:
            return text, []
        
        detections = []
        masked_text = text
        
        # Find all MAC addresses
        for match in self.MAC_PATTERN.finditer(text):
            mac_address = match.group(0)
            detections.append({
                "type": "mac_address",
                "value": mac_address,
                "start": match.start(),
                "end": match.end()
            })
            
            # Apply masking strategy
            if self.mac_mask_strategy == "partial":
                # Show first 8 characters, mask the rest
                masked = f"{mac_address[:8]}:**:**:**"
            elif self.mac_mask_strategy == "redact":
                masked = "[MAC_REDACTED]"
            elif self.mac_mask_strategy == "hash":
                # Hash the MAC address
                masked = hashlib.sha256(mac_address.encode()).hexdigest()[:16]
            elif self.mac_mask_strategy == "remove":
                masked = ""
            else:
                # Default: full mask
                masked = "XX:XX:XX:XX:XX:XX"
            
            masked_text = masked_text.replace(mac_address, masked)
        
        if detections:
            logger.info("Detected %d MAC address(es) in text", len(detections))
        
        return masked_text, detections
    
    def _process_dict_for_mac(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Recursively process a dictionary to detect and mask MAC addresses.
        
        Args:
            data: Dictionary to process
            
        Returns:
            Tuple of (processed_dict, was_modified)
        """
        modified = False
        result = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                masked_value, detections = self._detect_and_mask_mac(value)
                if detections:
                    result[key] = masked_value
                    modified = True
                else:
                    result[key] = value
            elif isinstance(value, dict):
                processed_value, was_modified = self._process_dict_for_mac(value)
                result[key] = processed_value
                modified = modified or was_modified
            elif isinstance(value, list):
                processed_list = []
                for item in value:
                    if isinstance(item, str):
                        masked_item, detections = self._detect_and_mask_mac(item)
                        if detections:
                            processed_list.append(masked_item)
                            modified = True
                        else:
                            processed_list.append(item)
                    elif isinstance(item, dict):
                        processed_item, was_modified = self._process_dict_for_mac(item)
                        processed_list.append(processed_item)
                        modified = modified or was_modified
                    else:
                        processed_list.append(item)
                result[key] = processed_list
            else:
                result[key] = value
        
        return result, modified
    
    async def prompt_pre_fetch(
        self, payload: PromptPrehookPayload, context: PluginContext
    ) -> PromptPrehookResult:
        """Process prompt before fetching, checking for PII and MAC addresses.
        
        Args:
            payload: The prompt payload
            context: Plugin execution context
            
        Returns:
            Result indicating whether to continue processing
        """
        # First, run base PII filter
        result = await self.base_filter.prompt_pre_fetch(payload, context)
        
        if not result.continue_processing:
            return result
        
        # Then check for MAC addresses
        if self.detect_mac and payload.args:
            processed_args, modified = self._process_dict_for_mac(payload.args)
            
            if modified:
                # Store detection in context
                if "na_pii_detections" not in context.state:
                    context.state["na_pii_detections"] = []
                context.state["na_pii_detections"].append({
                    "hook": "prompt_pre_fetch",
                    "type": "mac_address"
                })
                
                # Update payload
                if result.modified_payload:
                    result.modified_payload.args = processed_args
                else:
                    new_payload = PromptPrehookPayload(
                        prompt_id=payload.prompt_id,
                        args=processed_args
                    )
                    result.modified_payload = new_payload
        
        return result
    
    async def prompt_post_fetch(
        self, payload: PromptPosthookPayload, context: PluginContext
    ) -> PromptPosthookResult:
        """Process prompt after fetching, checking for PII and MAC addresses.
        
        Args:
            payload: The prompt result payload
            context: Plugin execution context
            
        Returns:
            Result with potentially modified messages
        """
        # Run base filter
        result = await self.base_filter.prompt_post_fetch(payload, context)
        
        # Check messages for MAC addresses
        if self.detect_mac and payload.result and payload.result.messages:
            modified = False
            
            for message in payload.result.messages:
                if hasattr(message.content, 'text') and message.content.text:
                    masked_text, detections = self._detect_and_mask_mac(message.content.text)
                    if detections:
                        message.content.text = masked_text
                        modified = True
            
            if modified:
                if not result.modified_payload:
                    result.modified_payload = payload
        
        return result
    
    async def tool_pre_invoke(
        self, payload: ToolPreInvokePayload, context: PluginContext
    ) -> ToolPreInvokeResult:
        """Process tool arguments before invocation.
        
        Args:
            payload: Tool invocation payload
            context: Plugin execution context
            
        Returns:
            Result indicating whether to continue
        """
        # Run base filter
        result = await self.base_filter.tool_pre_invoke(payload, context)
        
        if not result.continue_processing:
            return result
        
        # Check tool arguments for MAC addresses
        if self.detect_mac and payload.arguments:
            processed_args, modified = self._process_dict_for_mac(payload.arguments)
            
            if modified:
                if result.modified_payload:
                    result.modified_payload.arguments = processed_args
                else:
                    new_payload = ToolPreInvokePayload(
                        tool_name=payload.tool_name,
                        arguments=processed_args
                    )
                    result.modified_payload = new_payload
        
        return result
    
    async def tool_post_invoke(
        self, payload: ToolPostInvokePayload, context: PluginContext
    ) -> ToolPostInvokeResult:
        """Process tool results after invocation.
        
        Args:
            payload: Tool result payload
            context: Plugin execution context
            
        Returns:
            Result with potentially modified tool output
        """
        # Run base filter
        result = await self.base_filter.tool_post_invoke(payload, context)
        
        # Check tool result for MAC addresses
        if self.detect_mac and payload.result:
            # Handle different result types
            if isinstance(payload.result, str):
                masked_result, detections = self._detect_and_mask_mac(payload.result)
                if detections:
                    if result.modified_payload:
                        result.modified_payload.result = masked_result
                    else:
                        new_payload = ToolPostInvokePayload(
                            tool_name=payload.tool_name,
                            result=masked_result
                        )
                        result.modified_payload = new_payload
            elif isinstance(payload.result, dict):
                processed_result, modified = self._process_dict_for_mac(payload.result)
                if modified:
                    if result.modified_payload:
                        result.modified_payload.result = processed_result
                    else:
                        new_payload = ToolPostInvokePayload(
                            tool_name=payload.tool_name,
                            result=processed_result
                        )
                        result.modified_payload = new_payload
        
        return result

# Made with Bob
