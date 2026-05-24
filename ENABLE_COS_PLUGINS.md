# Enable COS Plugin Loading - Final Steps

## Current Status ✅
- ✅ Application is running with `PLUGINS_CONFIG_SOURCE=local`
- ✅ Fixed config file uploaded to COS bucket `contextforge-plugins`
- ✅ Config file has required `kind: python` field
- ✅ Standalone PII filter plugin ready in COS

## Enable COS Plugin Loading

### Step 1: Update Environment Variable in IBM Code Engine

1. Go to IBM Code Engine Console: https://cloud.ibm.com/codeengine/projects
2. Select your project
3. Click on `context-forge-2` application
4. Click **Environment variables** tab
5. Find `PLUGINS_CONFIG_SOURCE`
6. Change value from `local` to `both`
7. Click **Save**
8. Wait 2-3 minutes for restart

### Step 2: Verify Plugin Loading

After restart, check the logs:
```bash
ibmcloud ce app logs --name context-forge-2 --follow
```

Look for these success messages:
```
INFO: COS plugin loader initialized
INFO: Loaded plugin: na_pii_filter_standalone
INFO: Plugin sync interval: 30 seconds
```

### Step 3: Test Plugin in Admin UI

1. Open your application URL
2. Navigate to `/admin/plugins`
3. You should see `na_pii_filter_standalone` listed
4. Status should show "Active"

## How COS Plugin Loading Works

### Auto-Sync Behavior
- **Sync Interval**: Every 30 seconds (configurable via `PLUGINS_COS_SYNC_INTERVAL`)
- **What it does**: Downloads plugins from COS and checks for updates
- **Config Path**: `plugins/config.yaml` in COS bucket
- **Local Cache**: `/tmp/contextforge-plugins` (in container)

### "Both" Mode Benefits
- ✅ Loads plugins from COS bucket
- ✅ Also loads local plugins from container
- ✅ No redeployment needed for COS plugin updates
- ✅ Local plugins provide fallback

### Adding New Plugins to COS

1. **Create your plugin file** (e.g., `my_plugin.py`)
2. **Upload plugin to COS**:
   ```bash
   ibmcloud cos object-put \
     --bucket contextforge-plugins \
     --key plugins/my_plugin.py \
     --body my_plugin.py
   ```

3. **Update config in COS**:
   ```bash
   # Edit plugins/config_cos.yaml locally
   # Add your plugin to the plugins: section
   
   ibmcloud cos object-put \
     --bucket contextforge-plugins \
     --key plugins/config.yaml \
     --body plugins/config_cos.yaml
   ```

4. **Wait 30 seconds** - Plugin auto-loads (no restart needed!)

## Current COS Configuration

**Bucket**: `contextforge-plugins`
**Files in COS**:
- `plugins/config.yaml` - Plugin configuration
- `plugins/na_pii_filter_standalone.py` - PII filter plugin

**Environment Variables**:
```bash
PLUGINS_ENABLED=true
PLUGINS_CONFIG_SOURCE=both
PLUGINS_COS_BUCKET=contextforge-plugins
PLUGINS_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud
PLUGINS_COS_CONFIG_PATH=plugins/config.yaml
PLUGINS_COS_SYNC_INTERVAL=30
```

## PII Filter Plugin Features

The `na_pii_filter_standalone` plugin detects and masks:
- ✅ MAC addresses (e.g., `00:1A:2B:3C:4D:5E`)
- ✅ Email addresses
- ✅ Social Security Numbers (SSN)
- ✅ Credit card numbers
- ✅ Phone numbers

**Masking Strategies**:
- `partial` - Shows first/last characters (e.g., `00:1A:***:4D:5E`)
- `redact` - Replaces with `[REDACTED]`
- `hash` - Replaces with SHA256 hash
- `remove` - Removes completely

## Troubleshooting

### If plugins don't load:
1. Check logs: `ibmcloud ce app logs --name context-forge-2`
2. Verify COS credentials are set correctly
3. Check bucket name and endpoint URL
4. Verify config file has `kind: python` field

### If you need to disable COS plugins:
Change `PLUGINS_CONFIG_SOURCE` back to `local`

### If you need to disable all plugins:
Change `PLUGINS_ENABLED` to `false`

## Next Steps

1. ✅ Change `PLUGINS_CONFIG_SOURCE` to `both`
2. ✅ Wait for restart
3. ✅ Check logs for success
4. ✅ Verify in `/admin/plugins` UI
5. ✅ Test PII detection by making API calls

**You now have dynamic plugin loading without redeployment! 🎉**