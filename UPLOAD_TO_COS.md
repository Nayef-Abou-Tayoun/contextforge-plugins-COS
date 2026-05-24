# Upload Plugin Files to COS - Quick Reference

## Files to Upload

You need to upload 2 files to your COS bucket:

1. **na_pii_filter_standalone.py** - The standalone plugin (no dependencies)
2. **config_cos.yaml** - The COS-specific configuration

## Upload Commands

```bash
# 1. Upload the standalone plugin
ibmcloud cos object-put \
  --bucket contextforge-plugins \
  --key plugins/na_pii_filter_standalone.py \
  --body plugins/na_pii_filter_standalone.py

# 2. Upload the COS config
ibmcloud cos object-put \
  --bucket contextforge-plugins \
  --key plugins/config_cos.yaml \
  --body plugins/config_cos.yaml
```

## Update Code Engine Configuration

After uploading, update the environment variable in Code Engine:

### Via IBM Cloud Console:
1. Go to Code Engine → Applications → **context-forge-2**
2. Click **Environment variables** tab
3. Find or add: `PLUGINS_COS_CONFIG_PATH`
4. Set value to: `plugins/config_cos.yaml`
5. **Optional**: Change `PLUGINS_CONFIG_SOURCE` from `both` to `cos` (for COS-only mode)
6. Click **Save** (app will auto-restart)

### Via CLI:
```bash
ibmcloud ce app update context-forge-2 \
  --env PLUGINS_COS_CONFIG_PATH=plugins/config_cos.yaml \
  --env PLUGINS_CONFIG_SOURCE=cos
```

## Verify Plugin Loaded

After restart (1-2 minutes):
1. Go to: `https://context-forge-2.2a5divs1z0xi.us-south.codeengine.appdomain.cloud/admin/plugins`
2. You should see: **NA_PIIFilterStandalonePlugin** with status "Active"

## What the Plugin Does

- ✅ Detects MAC addresses (AA:BB:CC:DD:EE:FF)
- ✅ Detects emails, SSN, credit cards, phone numbers
- ✅ Masks with partial strategy (shows first part: AA:BB:XX:XX:XX:XX)
- ✅ Works on all prompts and tool responses automatically

## Future Updates

To add or update plugins:
1. Upload new `.py` file to COS `plugins/` folder
2. Update `config_cos.yaml` in COS
3. Wait 30 seconds for auto-sync
4. Plugin appears in UI automatically!

**No rebuild or redeploy needed!** 🎉