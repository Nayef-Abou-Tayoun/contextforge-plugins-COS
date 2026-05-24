# -*- coding: utf-8 -*-
"""Standalone PII Filter Plugin with MAC Address Detection

Copyright 2026
SPDX-License-Identifier: Apache-2.0
Author: Nayef Abou Tayoun

This is a standalone plugin that detects and masks PII including MAC addresses,
without requiring external dependencies like cpex-pii-filter.
"""

import re
import hashlib
from typing import Dict, Any, List, Tuple, Optional

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
from mcpgateway.services.logging_service import LoggingService


class NA_PIIFilterStandalonePlugin(Plugin):
    """Standalone PII filter with MAC address detection.
    
    This plugin detects and masks:
    - MAC addresses (AA:BB:CC:DD:EE:FF format)
    - Email addresses
    - Credit card numbers
    - Social Security Numbers (SSN)
    - Phone numbers
    
    No external dependencies required - all detection logic is built-in.
    """

    def __init__(self, config: PluginConfig, context: PluginContext):
        super().__init__(config, context)
        self.logger = LoggingService()
        
        # Detection patterns
        self.mac_pattern = re.compile(r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        self.credit_card_pattern = re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b')
        self.phone_pattern = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
        
        # Configuration
        self.detect_mac = config.get("detect_computer_mac", True)
        self.detect_email = config.get("detect_email", True)
        self.detect_ssn = config.get("detect_ssn", True)
        self.detect_credit_card = config.get("detect_credit_card", True)
        self.detect_phone = config.get("detect_phone", True)
        
        self.mac_mask_strategy = config.get("mac_mask_strategy", "partial")
        self.email_mask_strategy = config.get("email_mask_strategy", "partial")
        self.ssn_mask_strategy = config.get("ssn_mask_strategy", "redact")
        self.credit_card_mask_strategy = config.get("credit_card_mask_strategy", "partial")
        self.phone_mask_strategy = config.get("phone_mask_strategy", "partial")
        
        self.logger.info(f"NA_PIIFilterStandalonePlugin initialized with MAC detection: {self.detect_mac}")

    def _mask_value(self, value: str, strategy: str, pii_type: str) -> str:
        """Apply masking strategy to a detected PII value."""
        if strategy == "redact":
            return f"[{pii_type.upper()}_REDACTED]"
        elif strategy == "hash":
            hash_val = hashlib.sha256(value.encode()).hexdigest()[:8]
            return f"[{pii_type.upper()}_{hash_val}]"
        elif strategy == "remove":
            return ""
        elif strategy == "partial":
            if pii_type == "mac":
                # Show first 2 octets: AA:BB:XX:XX:XX:XX
                parts = re.split(r'[:-]', value)
                if len(parts) == 6:
                    sep = ':' if ':' in value else '-'
                    return f"{parts[0]}{sep}{parts[1]}{sep}XX{sep}XX{sep}XX{sep}XX"
            elif pii_type == "email":
                # Show first char and domain: a***@example.com
                local, domain = value.split('@')
                return f"{local[0]}***@{domain}"
            elif pii_type == "credit_card":
                # Show last 4 digits: ****-****-****-1234
                digits = re.sub(r'[- ]', '', value)
                return f"****-****-****-{digits[-4:]}"
            elif pii_type == "phone":
                # Show area code: (123) ***-****
                digits = re.sub(r'[-.() ]', '', value)
                return f"({digits[:3]}) ***-****"
            elif pii_type == "ssn":
                # Show last 4: ***-**-1234
                parts = value.split('-')
                if len(parts) == 3:
                    return f"***-**-{parts[2]}"
        return value

    def _detect_and_mask(self, text: str) -> Tuple[str, List[str]]:
        """Detect and mask all PII in text."""
        if not isinstance(text, str):
            return text, []
        
        detections = []
        result = text
        
        # MAC addresses
        if self.detect_mac:
            for match in self.mac_pattern.finditer(text):
                mac = match.group(0)
                masked = self._mask_value(mac, self.mac_mask_strategy, "mac")
                result = result.replace(mac, masked)
                detections.append(f"MAC:{mac}")
        
        # Email addresses
        if self.detect_email:
            for match in self.email_pattern.finditer(text):
                email = match.group(0)
                masked = self._mask_value(email, self.email_mask_strategy, "email")
                result = result.replace(email, masked)
                detections.append(f"EMAIL:{email}")
        
        # SSN
        if self.detect_ssn:
            for match in self.ssn_pattern.finditer(text):
                ssn = match.group(0)
                masked = self._mask_value(ssn, self.ssn_mask_strategy, "ssn")
                result = result.replace(ssn, masked)
                detections.append(f"SSN:{ssn}")
        
        # Credit cards
        if self.detect_credit_card:
            for match in self.credit_card_pattern.finditer(text):
                cc = match.group(0)
                masked = self._mask_value(cc, self.credit_card_mask_strategy, "credit_card")
                result = result.replace(cc, masked)
                detections.append(f"CC:{cc}")
        
        # Phone numbers
        if self.detect_phone:
            for match in self.phone_pattern.finditer(text):
                phone = match.group(0)
                masked = self._mask_value(phone, self.phone_mask_strategy, "phone")
                result = result.replace(phone, masked)
                detections.append(f"PHONE:{phone}")
        
        return result, detections

    def _process_dict(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Recursively process dictionary for PII."""
        result = {}
        modified = False
        
        for key, value in data.items():
            if isinstance(value, str):
                masked_value, detections = self._detect_and_mask(value)
                if detections:
                    self.logger.info(f"Detected PII in field '{key}': {detections}")
                    modified = True
                result[key] = masked_value
            elif isinstance(value, dict):
                processed_value, was_modified = self._process_dict(value)
                result[key] = processed_value
                modified = modified or was_modified
            elif isinstance(value, list):
                processed_list = []
                for item in value:
                    if isinstance(item, str):
                        masked_item, detections = self._detect_and_mask(item)
                        if detections:
                            modified = True
                        processed_list.append(masked_item)
                    elif isinstance(item, dict):
                        processed_item, was_modified = self._process_dict(item)
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
        """Mask PII in prompt before fetching."""
        try:
            data = payload.data
            processed_data, modified = self._process_dict(data)
            
            if modified:
                self.logger.info("PII detected and masked in prompt pre-fetch")
            
            return PromptPrehookResult(data=processed_data, modified=modified)
        except Exception as e:
            self.logger.error(f"Error in prompt_pre_fetch: {e}")
            return PromptPrehookResult(data=payload.data, modified=False)

    async def prompt_post_fetch(
        self, payload: PromptPosthookPayload, context: PluginContext
    ) -> PromptPosthookResult:
        """Mask PII in prompt after fetching."""
        try:
            data = payload.data
            processed_data, modified = self._process_dict(data)
            
            if modified:
                self.logger.info("PII detected and masked in prompt post-fetch")
            
            return PromptPosthookResult(data=processed_data, modified=modified)
        except Exception as e:
            self.logger.error(f"Error in prompt_post_fetch: {e}")
            return PromptPosthookResult(data=payload.data, modified=False)

    async def tool_pre_invoke(
        self, payload: ToolPreInvokePayload, context: PluginContext
    ) -> ToolPreInvokeResult:
        """Mask PII in tool arguments before invocation."""
        try:
            data = payload.data
            processed_data, modified = self._process_dict(data)
            
            if modified:
                self.logger.info("PII detected and masked in tool pre-invoke")
            
            return ToolPreInvokeResult(data=processed_data, modified=modified)
        except Exception as e:
            self.logger.error(f"Error in tool_pre_invoke: {e}")
            return ToolPreInvokeResult(data=payload.data, modified=False)

    async def tool_post_invoke(
        self, payload: ToolPostInvokePayload, context: PluginContext
    ) -> ToolPostInvokeResult:
        """Mask PII in tool response after invocation."""
        try:
            data = payload.data
            processed_data, modified = self._process_dict(data)
            
            if modified:
                self.logger.info("PII detected and masked in tool post-invoke")
            
            return ToolPostInvokeResult(data=processed_data, modified=modified)
        except Exception as e:
            self.logger.error(f"Error in tool_post_invoke: {e}")
            return ToolPostInvokeResult(data=payload.data, modified=False)

# Made with Bob
