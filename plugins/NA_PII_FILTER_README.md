# NA_PIIFilterPlugin - Extended PII Filter with MAC Address Detection

## Overview

`NA_PIIFilterPlugin` is a custom extension of the base `PIIFilterPlugin` that adds MAC address (computer hardware address) detection and masking capabilities. This plugin wraps the existing PII filter and adds an additional layer of security for detecting and protecting MAC addresses in prompts and tool invocations.

## Author

Nayef Abou Tayoun

## Features

### Base PII Detection (from PIIFilterPlugin)
- Social Security Numbers (SSN)
- Credit card numbers
- Email addresses
- Phone numbers
- IP addresses
- AWS access keys
- API keys

### Extended Detection (New)
- **MAC Addresses**: Detects hardware addresses in formats like:
  - `AA:BB:CC:DD:EE:FF` (colon-separated)
  - `AA-BB-CC-DD-EE-FF` (hyphen-separated)

## Files

- **Plugin Code**: `plugins/na_pii_filter_plugin.py`
- **Configuration**: `plugins/config-na-pii-filter.yaml`
- **This README**: `plugins/NA_PII_FILTER_README.md`

## Configuration

### MAC Address Detection Settings

```yaml
config:
  # Enable MAC address detection
  detect_computer_mac: true
  
  # Choose masking strategy
  mac_mask_strategy: "partial"  # Options: partial | redact | hash | remove
```

### Masking Strategies

| Strategy | Example Input | Example Output | Use Case |
|----------|---------------|----------------|----------|
| `partial` | `AA:BB:CC:DD:EE:FF` | `AA:BB:CC:**:**:**` | Show prefix for debugging |
| `redact` | `AA:BB:CC:DD:EE:FF` | `[MAC_REDACTED]` | Complete anonymization |
| `hash` | `AA:BB:CC:DD:EE:FF` | `a1b2c3d4e5f6g7h8` | Consistent pseudonymization |
| `remove` | `AA:BB:CC:DD:EE:FF` | `` | Complete removal |

### Full Configuration Example

```yaml
- name: "NA_PIIFilterPlugin"
  kind: "plugins.na_pii_filter_plugin.NA_PIIFilterPlugin"
  description: "Extended PII Filter with MAC address detection"
  version: "1.0.0"
  author: "Nayef Abou Tayoun"
  hooks: 
    - "prompt_pre_fetch"
    - "prompt_post_fetch"
    - "tool_pre_invoke"
    - "tool_post_invoke"
  mode: "enforce"
  priority: 50
  config:
    # Base PII detection
    detect_ssn: true
    detect_credit_card: true
    detect_email: true
    detect_phone: false
    detect_ip_address: false
    detect_aws_keys: true
    detect_api_keys: true
    
    # MAC address detection (NEW)
    detect_computer_mac: true
    mac_mask_strategy: "partial"
    
    # Behavior
    block_on_detection: false
    log_detections: true
    include_detection_details: true
    
    # Whitelist
    whitelist_patterns:
      - "test@example.com"
      - "00:00:00:00:00:00"
```

## Usage

### Local Deployment

1. **Place the plugin file**:
   ```bash
   cp plugins/na_pii_filter_plugin.py plugins/
   ```

2. **Update your plugin configuration**:
   ```bash
   # Use the provided config or add to your existing config
   cp plugins/config-na-pii-filter.yaml plugins/config.yaml
   ```

3. **Enable plugins**:
   ```bash
   export PLUGINS_ENABLED=true
   export PLUGINS_CONFIG_FILE=plugins/config-na-pii-filter.yaml
   ```

4. **Restart the application**:
   ```bash
   make dev
   ```

### COS Deployment (No Redeployment Required!)

1. **Upload plugin to COS**:
   ```bash
   # Upload the plugin file
   ibmcloud cos object-put \
     --bucket contextforge-plugins-bucket \
     --key plugins/na_pii_filter_plugin.py \
     --body plugins/na_pii_filter_plugin.py
   
   # Upload the configuration
   ibmcloud cos object-put \
     --bucket contextforge-plugins-bucket \
     --key plugins/config.yaml \
     --body plugins/config-na-pii-filter.yaml
   ```

2. **Wait for auto-sync** (5 minutes) or restart the app

3. **Verify in UI**: Navigate to `/admin/plugins` and search for "NA_PII"

## Testing

### Test MAC Address Detection

```python
# Test input with MAC address
test_input = "My computer's MAC address is AA:BB:CC:DD:EE:FF"

# Expected output (with partial masking)
# "My computer's MAC address is AA:BB:CC:**:**:**"
```

### Test with Different Formats

```python
# Colon-separated
"MAC: 00:1A:2B:3C:4D:5E"  # Detected ✓

# Hyphen-separated  
"MAC: 00-1A-2B-3C-4D-5E"  # Detected ✓

# No separator (not detected)
"MAC: 001A2B3C4D5E"       # Not detected ✗
```

## How It Works

1. **Initialization**: The plugin wraps the base `PIIFilterPlugin` and adds MAC detection configuration
2. **Pre-fetch Hook**: Scans prompt arguments for MAC addresses before processing
3. **Post-fetch Hook**: Scans LLM responses for MAC addresses
4. **Tool Hooks**: Scans tool arguments and results for MAC addresses
5. **Masking**: Applies the configured masking strategy to detected MAC addresses
6. **Logging**: Records all detections for audit purposes

## Architecture

```
┌─────────────────────────────────┐
│   NA_PIIFilterPlugin            │
│   (Wrapper)                     │
│                                 │
│  ┌───────────────────────────┐ │
│  │  Base PIIFilterPlugin     │ │
│  │  (SSN, Email, CC, etc.)   │ │
│  └───────────────────────────┘ │
│                                 │
│  ┌───────────────────────────┐ │
│  │  MAC Address Detection    │ │
│  │  (New functionality)      │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
```

## Compliance

This plugin helps meet compliance requirements for:
- **GDPR**: Protects personal data including hardware identifiers
- **HIPAA**: Protects PHI that may include device identifiers
- **PCI DSS**: Additional layer of security for payment processing systems
- **SOC 2**: Demonstrates data protection controls

## Troubleshooting

### Plugin Not Loading

1. Check logs for initialization errors:
   ```bash
   ibmcloud ce app logs --name context-forge-2 | grep "NA_PIIFilterPlugin"
   ```

2. Verify the plugin file is in the correct location
3. Check that `cpex-pii-filter` package is installed (>= 0.3.2)

### MAC Addresses Not Being Detected

1. Verify `detect_computer_mac: true` in config
2. Check MAC address format (must be colon or hyphen-separated)
3. Review logs for detection messages

### Performance Issues

1. Consider disabling MAC detection for high-traffic endpoints
2. Use conditions to apply only to specific servers/tenants
3. Adjust priority to run after less expensive plugins

## Future Enhancements

Potential additions for future versions:
- IPv6 address detection
- IMEI/IMSI detection (mobile device identifiers)
- Custom regex pattern support
- Configurable whitelist per detection type
- Performance optimizations with caching

## Support

For issues or questions:
1. Check the main ContextForge documentation
2. Review the base PIIFilterPlugin documentation
3. Contact: Nayef Abou Tayoun

## License

Copyright 2026
SPDX-License-Identifier: Apache-2.0