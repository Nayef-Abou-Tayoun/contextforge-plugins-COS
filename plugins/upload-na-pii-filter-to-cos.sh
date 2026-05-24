#!/bin/bash
# Upload NA_PIIFilterPlugin to IBM Cloud Object Storage
# Author: Nayef Abou Tayoun

set -e

# Configuration
BUCKET="contextforge-plugins-bucket"
PLUGIN_FILE="plugins/na_pii_filter_plugin.py"
CONFIG_FILE="plugins/config-na-pii-filter.yaml"
README_FILE="plugins/NA_PII_FILTER_README.md"

echo "========================================="
echo "Uploading NA_PIIFilterPlugin to COS"
echo "========================================="
echo ""

# Check if files exist
if [ ! -f "$PLUGIN_FILE" ]; then
    echo "❌ Error: Plugin file not found: $PLUGIN_FILE"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

echo "✓ Files found"
echo ""

# Upload plugin file
echo "📤 Uploading plugin file..."
ibmcloud cos object-put \
    --bucket "$BUCKET" \
    --key "plugins/na_pii_filter_plugin.py" \
    --body "$PLUGIN_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Plugin file uploaded successfully"
else
    echo "❌ Failed to upload plugin file"
    exit 1
fi

# Upload configuration file
echo ""
echo "📤 Uploading configuration file..."
ibmcloud cos object-put \
    --bucket "$BUCKET" \
    --key "plugins/config.yaml" \
    --body "$CONFIG_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Configuration file uploaded successfully"
else
    echo "❌ Failed to upload configuration file"
    exit 1
fi

# Upload README (optional)
if [ -f "$README_FILE" ]; then
    echo ""
    echo "📤 Uploading README file..."
    ibmcloud cos object-put \
        --bucket "$BUCKET" \
        --key "plugins/NA_PII_FILTER_README.md" \
        --body "$README_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ README file uploaded successfully"
    else
        echo "⚠️  Warning: Failed to upload README file (non-critical)"
    fi
fi

echo ""
echo "========================================="
echo "✅ Upload Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Wait 5 minutes for auto-sync, or restart the app"
echo "2. Verify in UI: https://your-app-url/admin/plugins"
echo "3. Search for 'NA_PII' to find your plugin"
echo ""
echo "The plugin will automatically:"
echo "  - Detect MAC addresses in prompts and tool calls"
echo "  - Apply the configured masking strategy"
echo "  - Log all detections for audit"
echo ""

# Made with Bob
