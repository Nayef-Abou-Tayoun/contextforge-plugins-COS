# IBM COS Plugin Loading - Implementation Summary

This document summarizes the implementation of dynamic plugin loading from IBM Cloud Object Storage (COS) for ContextForge.

## Overview

The implementation enables ContextForge to load plugins dynamically from IBM COS without requiring redeployment to IBM Code Engine. This provides hot-reload capabilities, centralized plugin management, and simplified updates across multiple gateway instances.

## Files Created/Modified

### New Files

1. **`mcpgateway/services/plugin_cos_loader.py`** (227 lines)
   - Core COS plugin loader service
   - Handles download, caching, and background sync
   - Integrates with Redis pub/sub for cross-pod invalidation
   - Features:
     - Async download from COS bucket
     - SHA256 checksum-based change detection
     - Configurable sync interval (30-3600 seconds)
     - Local caching for performance
     - Graceful error handling

2. **`docs/docs/using/plugins/cos-plugin-loading.md`** (497 lines)
   - Comprehensive user documentation
   - Configuration guide
   - Usage examples
   - Troubleshooting section
   - Best practices

### Modified Files

1. **`mcpgateway/config.py`**
   - Added COS configuration settings to `Settings` class:
     - `plugins_enabled`: Enable plugin framework
     - `plugins_config_file`: Local config path
     - `plugins_config_source`: Source type (local/cos)
     - `plugins_cos_bucket`: COS bucket name
     - `plugins_cos_endpoint`: COS endpoint URL
     - `plugins_cos_api_key`: IBM Cloud API key
     - `plugins_cos_instance_id`: COS instance ID
     - `plugins_cos_config_path`: Config path in bucket
     - `plugins_cos_sync_interval`: Sync interval (seconds)
     - `plugins_local_cache_dir`: Local cache directory

2. **`mcpgateway/plugins/__init__.py`**
   - Added `initialize_plugin_factory_with_cos()` function
   - Added `shutdown_plugin_factory()` function
   - Integrates COS loader with existing plugin manager factory
   - Handles both local and COS plugin sources

3. **`mcpgateway/main.py`**
   - Updated `lifespan()` startup to use `initialize_plugin_factory_with_cos()`
   - Updated shutdown to use `shutdown_plugin_factory()`
   - Ensures proper COS loader lifecycle management

4. **`pyproject.toml`**
   - Added dependency: `ibm-cos-sdk>=2.13.6`

5. **`.env.example`**
   - Added COS configuration section with all environment variables
   - Includes descriptions and default values

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IBM Cloud Object Storage                  │
│                   (contextforge-plugins bucket)              │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Download & Sync (every 5 min)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              ContextForge Gateway (Code Engine)              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  COSPluginLoader                                       │ │
│  │  - Downloads plugins from COS                          │ │
│  │  - Caches to /tmp/contextforge-plugins                 │ │
│  │  - Detects changes via checksum                        │ │
│  │  - Background sync task                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  TenantPluginManagerFactory                            │ │
│  │  - Loads plugins from cache                            │ │
│  │  - Executes plugin hooks                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Redis Pub/Sub (invalidation)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           Other Gateway Instances (Auto-Reload)              │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Automatic Synchronization
- Background task polls COS at configurable intervals (default: 5 minutes)
- SHA256 checksum comparison detects changes
- Only downloads when changes detected

### 2. Hot Reload
- Redis pub/sub broadcasts cache invalidation to all pods
- All gateway instances reload plugins automatically
- No downtime or manual intervention required

### 3. Local Caching
- Plugins cached to `/tmp/contextforge-plugins` for fast access
- Reduces COS API calls and improves performance
- Cache survives between syncs

### 4. Error Handling
- Graceful fallback to cached plugins on COS errors
- Detailed error logging for troubleshooting
- Non-blocking failures (gateway continues running)

### 5. Security
- API key stored as Code Engine secret
- Supports IAM authentication
- Optional service instance ID for additional security

## Configuration Example

### Environment Variables (.env)

```bash
# Enable plugins with COS source
PLUGINS_ENABLED=true
PLUGINS_CONFIG_SOURCE=cos

# IBM COS Configuration
PLUGINS_COS_BUCKET=contextforge-plugins
PLUGINS_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud
PLUGINS_COS_API_KEY=your-ibm-cloud-api-key
PLUGINS_COS_SYNC_INTERVAL=300
```

### IBM Code Engine

```bash
# Create secret for API key
ibmcloud ce secret create cos-credentials \
  --from-literal PLUGINS_COS_API_KEY=your-api-key

# Update application
ibmcloud ce application update contextforge \
  --env PLUGINS_ENABLED=true \
  --env PLUGINS_CONFIG_SOURCE=cos \
  --env PLUGINS_COS_BUCKET=contextforge-plugins \
  --env PLUGINS_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud \
  --env-from-secret cos-credentials
```

## Usage Workflow

### 1. Upload Plugins to COS

```bash
# Using AWS CLI (S3-compatible)
aws s3 sync plugins/ s3://contextforge-plugins/plugins/ \
  --endpoint-url https://s3.us-south.cloud-object-storage.appdomain.cloud
```

### 2. Gateway Auto-Syncs

- Gateway downloads plugins on startup
- Background task syncs every 5 minutes (configurable)
- Changes detected via checksum comparison

### 3. Hot Reload Triggered

- On change detection, gateway:
  1. Downloads updated files
  2. Updates local cache
  3. Broadcasts invalidation via Redis
  4. All pods reload plugins

### 4. Verify

```bash
# Check logs
ibmcloud ce application logs --name contextforge --follow

# Expected output:
# "Initializing plugins from IBM Cloud Object Storage"
# "Downloaded config.yaml (changed: True, checksum: abc123)"
# "Downloaded 15 plugin files from COS"
# "Plugin factory initialized with 5 plugins"
```

## Testing

### Unit Tests Required

1. **COSPluginLoader Tests**
   - Test download functionality
   - Test checksum detection
   - Test sync loop
   - Test error handling
   - Mock COS client

2. **Integration Tests**
   - Test full startup with COS
   - Test hot reload via Redis
   - Test fallback to cache on errors
   - Test multi-pod synchronization

### Manual Testing

1. **Initial Load**
   ```bash
   # Start gateway with COS enabled
   # Verify plugins load from COS
   # Check logs for successful download
   ```

2. **Hot Reload**
   ```bash
   # Upload updated plugin to COS
   # Wait for sync interval
   # Verify plugin reloaded without restart
   ```

3. **Error Handling**
   ```bash
   # Simulate COS unavailability
   # Verify gateway uses cached plugins
   # Verify error logged but gateway continues
   ```

## Dependencies

- **ibm-cos-sdk** (>=2.13.6): IBM Cloud Object Storage SDK
  - Provides S3-compatible API for COS
  - Handles authentication and requests
  - Includes boto3 and botocore

## Migration Path

### From Local to COS

1. **Prepare**: Upload existing plugins to COS bucket
2. **Configure**: Set COS environment variables
3. **Deploy**: Update Code Engine application
4. **Verify**: Check logs for successful COS initialization
5. **Cleanup**: Remove local plugin files from image (optional)

### Rollback

If issues occur, rollback to local mode:

```bash
ibmcloud ce application update contextforge \
  --env PLUGINS_CONFIG_SOURCE=local \
  --env PLUGINS_CONFIG_FILE=plugins/config.yaml
```

## Performance Considerations

### COS API Costs
- Sync interval affects API call frequency
- Recommended: 300-600 seconds for production
- Monitor COS usage and costs

### Network Bandwidth
- Initial download: ~1-10 MB (depends on plugin count)
- Incremental syncs: Only changed files downloaded
- Use regional COS endpoint for best performance

### Local Cache
- `/tmp` is fast ephemeral storage on Code Engine
- Cache persists between syncs
- Cleared on pod restart (re-downloaded from COS)

## Security Considerations

1. **API Key Management**
   - Store in Code Engine secrets, not environment variables
   - Use service-specific API keys with minimal permissions
   - Rotate keys regularly

2. **Bucket Access**
   - Use IAM policies to restrict access
   - Enable bucket encryption at rest
   - Enable activity tracking for audit logs

3. **Plugin Validation**
   - Validate plugin code before uploading to COS
   - Use code signing for plugin integrity
   - Implement plugin sandboxing (future enhancement)

## Future Enhancements

1. **Plugin Versioning**
   - Support multiple plugin versions in COS
   - A/B testing capabilities
   - Gradual rollout strategies

2. **Admin UI Integration**
   - Upload plugins via Admin UI
   - View plugin sync status
   - Manual reload trigger

3. **Metrics and Monitoring**
   - Plugin sync success/failure metrics
   - Download duration tracking
   - Cache hit/miss rates

4. **Advanced Caching**
   - Persistent cache across pod restarts
   - Shared cache volume for multi-pod deployments
   - Cache warming on startup

## Support

For issues or questions:
- See full documentation: `docs/docs/using/plugins/cos-plugin-loading.md`
- Check troubleshooting section in docs
- Review gateway logs for error details
- Open GitHub issue with logs and configuration

## References

- [IBM Cloud Object Storage Documentation](https://cloud.ibm.com/docs/cloud-object-storage)
- [IBM Code Engine Documentation](https://cloud.ibm.com/docs/codeengine)
- [ContextForge Plugin Framework](../plugins.md)
- [Creating Custom Plugins](./creating-plugins.md)