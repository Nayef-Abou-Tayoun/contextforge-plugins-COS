# Using Both COS and Local Plugins

ContextForge now supports loading plugins from **both** IBM Cloud Object Storage (COS) and the local filesystem simultaneously.

## Configuration

Set the environment variable:

```bash
PLUGINS_CONFIG_SOURCE=both
```

## How It Works

1. **COS Plugins**: Downloaded from IBM COS bucket to `/tmp/contextforge-plugins/plugins/`
2. **Local Plugins**: Loaded from local `plugins/` directory
3. **Merged**: Both plugin lists are combined (COS plugins first, then local plugins)
4. **Python Path**: Both directories are added to `sys.path` for imports

## Example Setup

### On IBM Code Engine

```bash
# Set to "both" mode
ibmcloud ce app update --name context-forge-2 \
  --env PLUGINS_CONFIG_SOURCE=both

# COS credentials (already configured)
# PLUGINS_COS_BUCKET=contextforge-plugins
# PLUGINS_COS_ENDPOINT=https://...
# PLUGINS_COS_API_KEY=...
```

### Plugin Organization

**COS Bucket Structure:**
```
contextforge-plugins/
├── plugins/
│   ├── hello_world_plugin.py
│   └── custom_plugin.py
└── plugins/
    └── config.yaml
```

**Local Filesystem:**
```
plugins/
├── config.yaml
├── pii_guardian_plugin.py
└── other_local_plugin.py
```

**Result:** All plugins from both sources are loaded and available!

## Benefits

- **Keep existing local plugins** while adding COS plugins
- **No migration required** - existing plugins continue to work
- **Gradual transition** - move plugins to COS at your own pace
- **Hot reload** - COS plugins update automatically every 30 seconds
- **Local development** - test plugins locally before uploading to COS

## Switching Modes

### Local Only (Default)
```bash
PLUGINS_CONFIG_SOURCE=local
```
Only loads plugins from local `plugins/` directory.

### COS Only
```bash
PLUGINS_CONFIG_SOURCE=cos
```
Only loads plugins from IBM COS bucket.

### Both (Recommended for Production)
```bash
PLUGINS_CONFIG_SOURCE=both
```
Loads plugins from both COS and local filesystem.

## Plugin Priority

When using "both" mode:
1. COS plugins are loaded first
2. Local plugins are loaded second
3. If a plugin with the same name exists in both, the COS version takes precedence

## Troubleshooting

### Plugins Not Appearing

Check the application logs:
```bash
ibmcloud ce app logs --name context-forge-2 --follow
```

Look for:
- `"Loaded X plugins from COS for merging"`
- `"Merged X COS plugins + Y local plugins = Z total"`
- `"Plugin factory initialized with Z plugins"`

### COS Connection Issues

Verify COS credentials:
```bash
ibmcloud ce app get --name context-forge-2 --output json | jq '.spec.template.spec.containers[0].env'
```

Ensure these are set:
- `PLUGINS_COS_BUCKET`
- `PLUGINS_COS_ENDPOINT`
- `PLUGINS_COS_API_KEY`

### Python Import Errors

Both plugin directories are added to Python's `sys.path`:
- `/tmp/contextforge-plugins/plugins/` (COS)
- `plugins/` (local)

Check logs for:
- `"Added COS plugin directory to Python path"`
- `"Added local plugin directory to Python path"`