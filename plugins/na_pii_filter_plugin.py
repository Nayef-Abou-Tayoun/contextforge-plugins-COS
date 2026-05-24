# -*- coding: utf-8 -*-
"""NA PII Filter Plugin with MAC Address Masking

Copyright 2026
SPDX-License-Identifier: Apache-2.0

Enhanced PII detection plugin that masks sensitive North American data including:
- Social Security Numbers (SSN)
- Credit Card Numbers
- Phone Numbers
- Email Addresses
- MAC Addresses (NEW!)

Supports multiple masking strategies: partial, redact, hash, remove
"""

import hashlib
import logging
import re
from typing import Any, Dict, Optional, Tuple

from cpex.framework import (
    Plugin,
    PluginConfig,
    PluginContext,
    ToolPreInvokePayload,
    ToolPreInvokeResult,
    ToolPostInvokePayload,
    ToolPostInvokeResult,
    PromptPrehookPayload,
    PromptPrehookResult,
)


class NA_PIIFilterPlugin(Plugin):
    """Enhanced PII detection and masking plugin with MAC address support.
    
    Detects and masks various types of PII in tool arguments and responses:
    - SSN (Social Security Numbers)
    - Credit Cards
    - Phone Numbers
    - Email Addresses
    - MAC Addresses
    
    Supports configurable masking strategies per PII type.
    """

    # Regex patterns for PII detection
    PATTERNS = {
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'credit_card': re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
        'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'mac_address': re.compile(r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b'),
    }

    def __init__(self, config: PluginConfig):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        cfg = self._config.config
        
        # Enable/disable specific PII types
        self.detect_ssn = cfg.get("detect_ssn", True)
        self.detect_credit_card = cfg.get("detect_credit_card", True)
        self.detect_phone = cfg.get("detect_phone", True)
        self.detect_email = cfg.get("detect_email", True)
        self.detect_mac_address = cfg.get("detect_mac_address", True)
        
        # Masking strategies per type
        self.ssn_strategy = cfg.get("ssn_strategy", "partial")
        self.credit_card_strategy = cfg.get("credit_card_strategy", "partial")
        self.phone_strategy = cfg.get("phone_strategy", "partial")
        self.email_strategy = cfg.get("email_strategy", "partial")
        self.mac_strategy = cfg.get("mac_strategy", "partial")
        
        # Statistics
        self.pii_detected_count = 0
        self.pii_masked_count = 0
        
        self.logger.info(
            f"NA_PIIFilterPlugin initialized - "
            f"MAC detection: {self.detect_mac_address}, "
            f"Default strategy: {self.mac_strategy}"
        )

    def _mask_value(self, value: str, pii_type: str, strategy: str) -> str:
        """Apply masking strategy to a PII value.
        
        Args:
            value: The PII value to mask
            pii_type: Type of PII (ssn, credit_card, phone, email, mac_address)
            strategy: Masking strategy (partial, redact, hash, remove)
            
        Returns:
            Masked value
        """
        if strategy == "redact":
            return f"[REDACTED_{pii_type.upper()}]"
        
        elif strategy == "hash":
            hash_obj = hashlib.sha256(value.encode())
            return f"[HASH_{hash_obj.hexdigest()[:8]}]"
        
        elif strategy == "remove":
            return ""
        
        elif strategy == "partial":
            # Partial masking - show first and last characters/segments
            if pii_type == "ssn":
                # Show first 3 digits: 123-**-****
                return f"{value[:3]}-**-****"
            
            elif pii_type == "credit_card":
                # Show last 4 digits: ****-****-****-1234
                clean = value.replace("-", "").replace(" ", "")
                return f"****-****-****-{clean[-4:]}"
            
            elif pii_type == "phone":
                # Show area code: (123) ***-****
                clean = re.sub(r'[^0-9]', '', value)
                return f"({clean[:3]}) ***-****"
            
            elif pii_type == "email":
                # Show first char and domain: j***@example.com
                parts = value.split("@")
                if len(parts) == 2:
                    return f"{parts[0][0]}***@{parts[1]}"
                return "[MASKED_EMAIL]"
            
            elif pii_type == "mac_address":
                # Show first and last octet: 00:1A:**:**:**:5E
                parts = re.split(r'[:-]', value)
                if len(parts) == 6:
                    sep = ":" if ":" in value else "-"
                    return f"{parts[0]}{sep}{parts[1]}{sep}**{sep}**{sep}**{sep}{parts[5]}"
                return "[MASKED_MAC]"
        
        return value

    def _scan_and_mask(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Scan text for PII and apply masking.
        
        Args:
            text: Text to scan
            
        Returns:
            Tuple of (masked_text, detection_counts)
        """
        if not isinstance(text, str):
            return text, {}
        
        masked_text = text
        counts = {}
        
        # Scan for each PII type
        if self.detect_ssn:
            matches = self.PATTERNS['ssn'].findall(masked_text)
            if matches:
                counts['ssn'] = len(matches)
                for match in matches:
                    masked = self._mask_value(match, 'ssn', self.ssn_strategy)
                    masked_text = masked_text.replace(match, masked)
        
        if self.detect_credit_card:
            matches = self.PATTERNS['credit_card'].findall(masked_text)
            if matches:
                counts['credit_card'] = len(matches)
                for match in matches:
                    masked = self._mask_value(match, 'credit_card', self.credit_card_strategy)
                    masked_text = masked_text.replace(match, masked)
        
        if self.detect_phone:
            matches = self.PATTERNS['phone'].findall(masked_text)
            if matches:
                counts['phone'] = len(matches)
                for match in matches:
                    masked = self._mask_value(match, 'phone', self.phone_strategy)
                    masked_text = masked_text.replace(match, masked)
        
        if self.detect_email:
            matches = self.PATTERNS['email'].findall(masked_text)
            if matches:
                counts['email'] = len(matches)
                for match in matches:
                    masked = self._mask_value(match, 'email', self.email_strategy)
                    masked_text = masked_text.replace(match, masked)
        
        if self.detect_mac_address:
            matches = self.PATTERNS['mac_address'].findall(masked_text)
            if matches:
                # matches is a list of tuples from the regex groups
                full_matches = [m[0] + m[1] for m in matches]
                counts['mac_address'] = len(full_matches)
                for match in full_matches:
                    masked = self._mask_value(match, 'mac_address', self.mac_strategy)
                    masked_text = masked_text.replace(match, masked)
        
        return masked_text, counts

    def _process_dict(self, data: Any) -> Tuple[Any, Dict[str, int]]:
        """Recursively process dictionary/list structures for PII.
        
        Args:
            data: Data structure to process
            
        Returns:
            Tuple of (processed_data, detection_counts)
        """
        total_counts: Dict[str, int] = {}
        
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                processed_value, counts = self._process_dict(value)
                result[key] = processed_value
                # Merge counts
                for pii_type, count in counts.items():
                    total_counts[pii_type] = total_counts.get(pii_type, 0) + count
            return result, total_counts
        
        elif isinstance(data, list):
            result = []
            for item in data:
                processed_item, counts = self._process_dict(item)
                result.append(processed_item)
                # Merge counts
                for pii_type, count in counts.items():
                    total_counts[pii_type] = total_counts.get(pii_type, 0) + count
            return result, total_counts
        
        elif isinstance(data, str):
            return self._scan_and_mask(data)
        
        else:
            return data, {}

    async def tool_pre_invoke(self, payload: ToolPreInvokePayload, context: PluginContext) -> ToolPreInvokeResult:
        """Scan and mask PII in tool arguments before invocation."""
        if hasattr(payload, 'arguments') and payload.arguments:
            masked_args, counts = self._process_dict(payload.arguments)
            
            if counts:
                self.pii_detected_count += sum(counts.values())
                self.pii_masked_count += sum(counts.values())
                
                self.logger.info(
                    f"🔒 PII Detected in tool '{payload.tool_name}' arguments: {counts}"
                )
                
                payload.arguments = masked_args
        
        return ToolPreInvokeResult(payload=payload)

    async def tool_post_invoke(self, payload: ToolPostInvokePayload, context: PluginContext) -> ToolPostInvokeResult:
        """Scan and mask PII in tool response."""
        if hasattr(payload, 'result') and payload.result:
            masked_result, counts = self._process_dict(payload.result)
            
            if counts:
                self.pii_detected_count += sum(counts.values())
                self.pii_masked_count += sum(counts.values())
                
                self.logger.info(
                    f"🔒 PII Detected in tool '{payload.tool_name}' response: {counts}"
                )
                
                payload.result = masked_result
        
        return ToolPostInvokeResult(payload=payload)

    async def prompt_prehook(self, payload: PromptPrehookPayload, context: PluginContext) -> PromptPrehookResult:
        """Scan and mask PII in prompt arguments."""
        if hasattr(payload, 'arguments') and payload.arguments:
            masked_args, counts = self._process_dict(payload.arguments)
            
            if counts:
                self.pii_detected_count += sum(counts.values())
                self.pii_masked_count += sum(counts.values())
                
                self.logger.info(
                    f"🔒 PII Detected in prompt '{payload.name}' arguments: {counts}"
                )
                
                payload.arguments = masked_args
        
        return PromptPrehookResult(payload=payload)


# Made with Bob