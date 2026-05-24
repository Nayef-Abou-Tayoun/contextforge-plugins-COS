#!/bin/bash
# Diagnostic script to check ContextForge plugin configuration

echo "=== ContextForge Plugin Configuration Checker ==="
echo ""

# Check if running in Code Engine
if [ -n "$CE_APP" ]; then
    echo "✓ Running in IBM Code Engine"
    echo "  App: $CE_APP"
    echo ""
fi

# Check plugin environment variables
echo "Plugin Configuration:"
echo "  PLUGINS_ENABLED: ${PLUGINS_ENABLED:-not set}"
echo "  PLUGINS_CONFIG_SOURCE: ${PLUGINS_CONFIG_SOURCE:-not set}"
echo "  PLUGINS_CONFIG_FILE: ${PLUGINS_CONFIG_FILE:-not set}"
echo ""

# Check COS configuration
echo "COS Configuration:"
echo "  PLUGINS_COS_BUCKET: ${PLUGINS_COS_BUCKET:-not set}"
echo "  PLUGINS_COS_ENDPOINT: ${PLUGINS_COS_ENDPOINT:-not set}"
echo "  PLUGINS_COS_API_KEY: ${PLUGINS_COS_API_KEY:+***set***}"
echo "  PLUGINS_COS_CONFIG_PATH: ${PLUGINS_COS_CONFIG_PATH:-not set}"
echo "  PLUGINS_COS_SYNC_INTERVAL: ${PLUGINS_COS_SYNC_INTERVAL:-not set}"
echo ""

# Check if cpex-pii-filter is installed
echo "Checking cpex-pii-filter package:"
if python -c "import cpex_pii_filter" 2>/dev/null; then
    echo "  ✓ cpex-pii-filter is installed"
    python -c "import cpex_pii_filter; print(f'  Version: {cpex_pii_filter.__version__ if hasattr(cpex_pii_filter, \"__version__\") else \"unknown\"}')" 2>/dev/null || echo "  Version: unknown"
else
    echo "  ✗ cpex-pii-filter is NOT installed"
fi
echo ""

# Check if config file exists locally
if [ -n "$PLUGINS_CONFIG_FILE" ] && [ -f "$PLUGINS_CONFIG_FILE" ]; then
    echo "Local config file found: $PLUGINS_CONFIG_FILE"
    echo "  First 10 lines:"
    head -10 "$PLUGINS_CONFIG_FILE" | sed 's/^/    /'
else
    echo "Local config file not found or not set"
fi
echo ""

# Recommendations
echo "=== Recommendations ==="
if [ "$PLUGINS_ENABLED" != "true" ]; then
    echo "⚠️  Set PLUGINS_ENABLED=true"
fi

if [ "$PLUGINS_CONFIG_SOURCE" != "cos" ] && [ "$PLUGINS_CONFIG_SOURCE" != "both" ]; then
    echo "⚠️  Set PLUGINS_CONFIG_SOURCE=cos or PLUGINS_CONFIG_SOURCE=both"
fi

if [ -z "$PLUGINS_COS_BUCKET" ]; then
    echo "⚠️  Set PLUGINS_COS_BUCKET to your COS bucket name"
fi

if [ -z "$PLUGINS_COS_ENDPOINT" ]; then
    echo "⚠️  Set PLUGINS_COS_ENDPOINT to your COS endpoint URL"
fi

if [ -z "$PLUGINS_COS_API_KEY" ]; then
    echo "⚠️  Set PLUGINS_COS_API_KEY to your IBM Cloud API key"
fi

echo ""
echo "=== Quick Fix Commands ==="
echo "For IBM Code Engine, run these commands:"
echo ""
echo "# Enable plugins and set COS as source"
echo "ibmcloud ce app update contextforge \\"
echo "  --env PLUGINS_ENABLED=true \\"
echo "  --env PLUGINS_CONFIG_SOURCE=cos \\"
echo "  --env PLUGINS_COS_BUCKET=contextforge-plugins \\"
echo "  --env PLUGINS_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud \\"
echo "  --env PLUGINS_COS_CONFIG_PATH=plugins/config-na-pii-filter.yaml \\"
echo "  --env PLUGINS_COS_API_KEY=YOUR_API_KEY"
echo ""

# Made with Bob
