# Dynamic Plugin Loading from IBM Cloud Object Storage

ContextForge supports loading plugins dynamically from IBM Cloud Object Storage (COS) without requiring gateway redeployment. This enables centralized plugin management, hot-reload capabilities, and simplified plugin updates across multiple gateway instances.

## Overview

### Benefits

- **No Redeployment Required**: Update plugins without restarting or redeploying the gateway
- **Hot Reload**: Automatic plugin synchronization and reload across all gateway pods
- **Centralized Management**: Store plugins in a single COS bucket accessible by all instances
- **Version Control**: Maintain plugin versions in COS with rollback support
- **Multi-Environment**: Use different COS buckets for dev/staging/production

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IBM Cloud Object Storage                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Bucket: contextforge-plugins                          │ │
│  │  ├── plugins/config.yaml                               │ │
│  │  ├── plugins/my_plugin/                                │ │
│  │  │   ├── __init__.py                                   │ │
│  │  │   ├── my_plugin.py                                  │ │
│  │  │   └── plugin-manifest.yaml                          │ │
│  │  └── plugins/another_plugin/...                        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Download & Sync (every 5 min)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              ContextForge Gateway (Code Engine)              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Local Cache: /tmp/contextforge-plugins                │ │
│  │  ├── config.yaml                                       │ │
│  │  └── plugins/...                                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            │ Load & Execute                  │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Plugin Manager Factory                         │ │
│  │  - Loads plugins from cache                            │ │
│  │  - Executes plugin hooks                               │ │
│  │  - Invalidates cache on changes                        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Redis Pub/Sub
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           Other Gateway Instances (Auto-Reload)              │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Prerequisites

1. **IBM Cloud Account** with Cloud Object Storage service
2. **COS Bucket** created for plugin storage
3. **API Key** with read access to the COS bucket
4. **Redis** instance for cross-pod cache invalidation

### Environment Variables

Add these variables to your `.env` file or Code Engine application configuration:

```bash
# Enable plugins
PLUGINS_ENABLED=true

# Set COS as the plugin source
PLUGINS_CONFIG_SOURCE=cos

# IBM COS Configuration
PLUGINS_COS_BUCKET=contextforge-plugins
PLUGINS_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud
PLUGINS_COS_API_KEY=your-ibm-cloud-api-key
PLUGINS_COS_INSTANCE_ID=  # Optional, can be empty

# Optional: Customize paths and sync interval
PLUGINS_COS_CONFIG_PATH=plugins/config.yaml
PLUGINS_COS_SYNC_INTERVAL=300  # 5 minutes
PLUGINS_LOCAL_CACHE_DIR=/tmp/contextforge-plugins
```

### IBM Code Engine Configuration

Configure your Code Engine application with COS credentials:

```bash
# Create secret for COS API key
ibmcloud ce secret create cos-credentials \
  --from-literal PLUGINS_COS_API_KEY=your-api-key

# Update application with COS configuration
ibmcloud ce application update contextforge \
  --env PLUGINS_ENABLED=true \
  --env PLUGINS_CONFIG_SOURCE=cos \
  --env PLUGINS_COS_BUCKET=contextforge-plugins \
  --env PLUGINS_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud \
  --env PLUGINS_COS_SYNC_INTERVAL=300 \
  --env-from-secret cos-credentials
```

## Usage

### 1. Prepare Plugin Files

Organize your plugins in the following structure:

```
plugins/
├── config.yaml                    # Main plugin configuration
├── my_plugin/
│   ├── __init__.py
│   ├── my_plugin.py
│   └── plugin-manifest.yaml
└── another_plugin/
    ├── __init__.py
    ├── another_plugin.py
    └── plugin-manifest.yaml
```

### 2. Upload to COS

#### Using IBM Cloud CLI

```bash
# Install IBM Cloud CLI and COS plugin
ibmcloud plugin install cloud-object-storage

# Upload plugins directory
ibmcloud cos upload \
  --bucket contextforge-plugins \
  --key plugins/config.yaml \
  --file plugins/config.yaml

# Upload plugin directories recursively
for plugin in plugins/*/; do
  ibmcloud cos upload \
    --bucket contextforge-plugins \
    --key "$plugin" \
    --file "$plugin" \
    --recursive
done
```

#### Using AWS CLI (S3-compatible)

```bash
# Configure AWS CLI for IBM COS
aws configure set aws_access_key_id <access_key>
aws configure set aws_secret_access_key <secret_key>

# Upload plugins
aws s3 sync plugins/ s3://contextforge-plugins/plugins/ \
  --endpoint-url https://s3.us-south.cloud-object-storage.appdomain.cloud
```

#### Using Python SDK

```python
import ibm_boto3
from ibm_botocore.client import Config

# Initialize COS client
cos = ibm_boto3.client(
    "s3",
    ibm_api_key_id="your-api-key",
    ibm_service_instance_id="",
    config=Config(signature_version="oauth"),
    endpoint_url="https://s3.us-south.cloud-object-storage.appdomain.cloud"
)

# Upload config.yaml
cos.upload_file(
    "plugins/config.yaml",
    "contextforge-plugins",
    "plugins/config.yaml"
)

# Upload plugin files
import os
for root, dirs, files in os.walk("plugins"):
    for file in files:
        local_path = os.path.join(root, file)
        cos_key = local_path
        cos.upload_file(local_path, "contextforge-plugins", cos_key)
```

### 3. Verify Plugin Loading

Check gateway logs for successful plugin loading:

```bash
# View Code Engine logs
ibmcloud ce application logs --name contextforge --follow

# Look for these log messages:
# "Initializing plugins from IBM Cloud Object Storage"
# "Downloaded config.yaml (changed: True, checksum: abc123)"
# "Downloaded 15 plugin files from COS"
# "Plugin factory initialized with 5 plugins"
# "Started COS plugin sync background task"
```

### 4. Update Plugins

To update plugins without redeployment:

1. **Modify plugin files locally**
2. **Upload to COS** (overwrites existing files)
3. **Wait for sync** (default: 5 minutes) or trigger manual reload

The gateway will:
- Detect changes via checksum comparison
- Download updated files
- Invalidate plugin cache
- Reload plugins across all pods via Redis pub/sub

### 5. Manual Plugin Reload (Optional)

Force immediate plugin reload via API:

```bash
# Trigger manual reload
curl -X POST https://your-gateway.com/admin/plugins/reload \
  -H "Authorization: Bearer $TOKEN"
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PLUGINS_ENABLED` | Yes | `false` | Enable plugin framework |
| `PLUGINS_CONFIG_SOURCE` | No | `local` | Plugin source: `local` or `cos` |
| `PLUGINS_COS_BUCKET` | Yes* | - | COS bucket name (*required when source=cos) |
| `PLUGINS_COS_ENDPOINT` | Yes* | - | COS endpoint URL (*required when source=cos) |
| `PLUGINS_COS_API_KEY` | Yes* | - | IBM Cloud API key (*required when source=cos) |
| `PLUGINS_COS_INSTANCE_ID` | No | `""` | COS service instance ID |
| `PLUGINS_COS_CONFIG_PATH` | No | `plugins/config.yaml` | Path to config in bucket |
| `PLUGINS_COS_SYNC_INTERVAL` | No | `300` | Sync interval in seconds (30-3600) |
| `PLUGINS_LOCAL_CACHE_DIR` | No | `/tmp/contextforge-plugins` | Local cache directory |

### COS Bucket Structure

```
contextforge-plugins/
├── plugins/
│   ├── config.yaml              # Main configuration (required)
│   ├── plugin1/
│   │   ├── __init__.py
│   │   ├── plugin1.py
│   │   └── plugin-manifest.yaml
│   ├── plugin2/
│   │   ├── __init__.py
│   │   ├── plugin2.py
│   │   └── plugin-manifest.yaml
│   └── ...
```

## Troubleshooting

### Plugin Loading Failures

**Symptom**: Gateway fails to start with plugin errors

**Solutions**:
1. Check COS credentials are correct
2. Verify bucket name and endpoint URL
3. Ensure API key has read permissions
4. Check `config.yaml` syntax is valid
5. Review gateway logs for specific errors

```bash
# Test COS connectivity
ibmcloud cos list-objects --bucket contextforge-plugins

# Verify config.yaml syntax
python -c "import yaml; yaml.safe_load(open('plugins/config.yaml'))"
```

### Sync Not Working

**Symptom**: Plugin updates not reflected after upload to COS

**Solutions**:
1. Check sync interval hasn't elapsed yet
2. Verify file checksums changed in COS
3. Check Redis connectivity for cache invalidation
4. Review sync task logs

```bash
# Check sync interval
echo $PLUGINS_COS_SYNC_INTERVAL

# Force manual reload
curl -X POST https://your-gateway.com/admin/plugins/reload \
  -H "Authorization: Bearer $TOKEN"
```

### Cache Issues

**Symptom**: Old plugin versions still executing

**Solutions**:
1. Clear local cache directory
2. Restart gateway pods
3. Verify Redis pub/sub is working

```bash
# Clear cache (Code Engine)
ibmcloud ce application update contextforge --env PLUGINS_LOCAL_CACHE_DIR=/tmp/plugins-$(date +%s)

# Restart application
ibmcloud ce application update contextforge --scale-down-delay=0
```

### Permission Errors

**Symptom**: `403 Forbidden` or `Access Denied` errors

**Solutions**:
1. Verify API key has `Reader` role on bucket
2. Check bucket policies allow access
3. Ensure service instance ID is correct (if required)

```bash
# Test API key permissions
ibmcloud cos list-objects \
  --bucket contextforge-plugins \
  --ibm-api-key-id your-api-key
```

## Best Practices

### Security

1. **Use IAM API Keys**: Create service-specific API keys with minimal permissions
2. **Restrict Bucket Access**: Use bucket policies to limit access to specific IPs/services
3. **Encrypt Secrets**: Store API keys in Code Engine secrets, not environment variables
4. **Audit Logging**: Enable COS activity tracking for plugin changes

### Performance

1. **Optimize Sync Interval**: Balance freshness vs. API costs (recommended: 300-600 seconds)
2. **Use Regional Endpoints**: Choose COS endpoint closest to Code Engine region
3. **Cache Locally**: Default cache directory (`/tmp`) is fast ephemeral storage
4. **Monitor Bandwidth**: Track COS egress costs for frequent syncs

### Reliability

1. **Version Control**: Tag plugin versions in COS (e.g., `plugins/v1.0.0/`)
2. **Test Before Upload**: Validate plugins locally before uploading to COS
3. **Gradual Rollout**: Use multiple buckets for staged deployments
4. **Rollback Plan**: Keep previous plugin versions in COS for quick rollback

### Cost Optimization

1. **Lifecycle Policies**: Archive old plugin versions to cheaper storage tiers
2. **Compression**: Compress plugin files before upload (gateway decompresses)
3. **Batch Updates**: Upload multiple plugin changes together to reduce API calls
4. **Monitor Usage**: Track COS API calls and storage costs

## Migration from Local to COS

### Step 1: Prepare COS Bucket

```bash
# Create bucket
ibmcloud cos bucket-create \
  --bucket contextforge-plugins \
  --region us-south

# Upload existing plugins
aws s3 sync plugins/ s3://contextforge-plugins/plugins/ \
  --endpoint-url https://s3.us-south.cloud-object-storage.appdomain.cloud
```

### Step 2: Update Configuration

```bash
# Update Code Engine application
ibmcloud ce application update contextforge \
  --env PLUGINS_CONFIG_SOURCE=cos \
  --env PLUGINS_COS_BUCKET=contextforge-plugins \
  --env PLUGINS_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud \
  --env-from-secret cos-credentials
```

### Step 3: Verify and Monitor

```bash
# Check logs for successful COS initialization
ibmcloud ce application logs --name contextforge --tail 100

# Verify plugins loaded
curl https://your-gateway.com/admin/plugins \
  -H "Authorization: Bearer $TOKEN"
```

### Step 4: Remove Local Files (Optional)

Once COS loading is confirmed working, you can remove local plugin files from the container image to reduce image size.

## Advanced Topics

### Multi-Region Deployment

Use COS replication for multi-region deployments:

```bash
# Enable cross-region replication
ibmcloud cos bucket-replication-put \
  --bucket contextforge-plugins \
  --replication-configuration file://replication.json
```

### Plugin Versioning Strategy

Organize plugins by version in COS:

```
plugins/
├── v1.0.0/
│   ├── config.yaml
│   └── plugin1/...
├── v1.1.0/
│   ├── config.yaml
│   └── plugin1/...
└── latest/  # Symlink or copy of current version
    ├── config.yaml
    └── plugin1/...
```

Update `PLUGINS_COS_CONFIG_PATH` to switch versions:
```bash
PLUGINS_COS_CONFIG_PATH=plugins/v1.1.0/config.yaml
```

### Monitoring and Alerting

Set up monitoring for plugin sync health:

```python
# Custom health check endpoint
@app.get("/health/plugins")
async def plugin_health():
    from mcpgateway.services.plugin_cos_loader import get_cos_loader
    
    loader = get_cos_loader()
    if loader:
        last_sync = loader._last_checksum
        return {"status": "healthy", "last_sync": last_sync}
    return {"status": "degraded", "reason": "COS loader not initialized"}
```

## See Also

- [Plugin Framework Overview](../plugins.md)
- [Creating Custom Plugins](./creating-plugins.md)
- [Plugin Configuration Reference](./plugin-config.md)
- [IBM Cloud Object Storage Documentation](https://cloud.ibm.com/docs/cloud-object-storage)