# Upload Plugins to IBM Cloud Object Storage

## Quick Start

Your IBM Code Engine application is configured and ready, but needs plugin files uploaded to COS bucket `contextforge-plugins`.

## Your COS Credentials

- **Bucket**: `contextforge-plugins`
- **Endpoint**: `https://s3.us-south.cloud-object-storage.appdomain.cloud`
- **API Key**: `wlm0CZNVSCYcHfWrNTOV3RTPDClLoZNJhCyFLHO7hYFj`
- **Access Key ID**: `b0b913488dff45bfa43699af0490bf7d`
- **Secret Access Key**: `ba2549209412a4f362d7bd756f712eb7851e6617e7534ee8`

## Upload Commands

### 1. Upload Plugin Configuration

```bash
# Upload the main plugin config file
ibmcloud cos object-put \
  --bucket contextforge-plugins \
  --key plugins/config.yaml \
  --body plugins/config.yaml
```

### 2. Upload Plugin Files

```bash
# Upload PII Guardian plugin
ibmcloud cos object-put \
  --bucket contextforge-plugins \
  --key plugins/pii_guardian.py \
  --body plugins/pii_guardian.py

# Upload PII Guardian policy config
ibmcloud cos object-put \
  --bucket contextforge-plugins \
  --key plugins/config-pii-guardian-policy.yaml \
  --body plugins/config-pii-guardian-policy.yaml
```

### 3. Verify Uploads

```bash
# List all objects in the bucket
ibmcloud cos objects --bucket contextforge-plugins

# Should show:
# - plugins/config.yaml
# - plugins/pii_guardian.py
# - plugins/config-pii-guardian-policy.yaml
```

## Alternative: Using AWS CLI

If you prefer using AWS CLI (compatible with IBM COS):

```bash
# Configure AWS CLI for IBM COS
aws configure set aws_access_key_id b0b913488dff45bfa43699af0490bf7d
aws configure set aws_secret_access_key ba2549209412a4f362d7bd756f712eb7851e6617e7534ee8
aws configure set region us-south

# Upload files
aws s3 cp plugins/config.yaml s3://contextforge-plugins/plugins/config.yaml \
  --endpoint-url https://s3.us-south.cloud-object-storage.appdomain.cloud

aws s3 cp plugins/pii_guardian.py s3://contextforge-plugins/plugins/pii_guardian.py \
  --endpoint-url https://s3.us-south.cloud-object-storage.appdomain.cloud

aws s3 cp plugins/config-pii-guardian-policy.yaml s3://contextforge-plugins/plugins/config-pii-guardian-policy.yaml \
  --endpoint-url https://s3.us-south.cloud-object-storage.appdomain.cloud

# List files
aws s3 ls s3://contextforge-plugins/plugins/ \
  --endpoint-url https://s3.us-south.cloud-object-storage.appdomain.cloud
```

## After Upload

Once files are uploaded, your Code Engine application will:
1. Automatically detect the files on next restart
2. Download and validate them
3. Start successfully with plugins enabled
4. Sync changes every 5 minutes automatically

## Check Application Status

```bash
# Check if application is running
ibmcloud ce application get --name context-forge-2

# View logs
ibmcloud ce application logs --name context-forge-2 --tail 50
```

## Expected Behavior

After successful upload, you should see in logs:
- ✅ "Downloaded plugin config from COS"
- ✅ "Plugin manager factory initialized successfully"
- ✅ Application status: "Ready"

## Troubleshooting

If application still fails:
1. Verify file paths are exactly `plugins/config.yaml` (case-sensitive)
2. Check that `plugins/config.yaml` references correct plugin filenames
3. Ensure all referenced plugins are uploaded
4. Review logs: `ibmcloud ce application logs --name context-forge-2`

## Future Updates

To update plugins without redeployment:
1. Upload new version to COS (same path)
2. Wait up to 5 minutes for automatic sync
3. Plugins hot-reload automatically

Or trigger immediate reload via Redis:
```bash
# Publish reload event (if Redis is accessible)
redis-cli PUBLISH plugin_reload '{"action": "reload"}'