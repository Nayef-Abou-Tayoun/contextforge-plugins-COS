# Cost Analysis Plugin - Quick COS Upload

## 🚀 Quick Upload (Copy & Paste)

### Step 1: Upload Plugin File

```bash
ibmcloud cos object-put \
  --bucket contextforge-plugins \
  --key plugins/cost_analysis_plugin.py \
  --body plugins/cost_analysis_plugin.py
```

### Step 2: Upload Configuration

```bash
ibmcloud cos object-put \
  --bucket contextforge-plugins \
  --key plugins/config_cost_analysis_cos.yaml \
  --body plugins/config_cost_analysis_cos.yaml
```

### Step 3: Verify Upload

```bash
ibmcloud cos objects --bucket contextforge-plugins --prefix plugins/ | grep cost_analysis
```

Expected output:
```
plugins/cost_analysis_plugin.py
plugins/config_cost_analysis_cos.yaml
```

## ✅ That's It!

Your Code Engine application will:
- Automatically detect the new plugin within 5 minutes
- Load and initialize the Cost Analysis plugin
- Start tracking token consumption and costs

## 🔍 Quick Verification

Check logs:
```bash
ibmcloud ce application logs --name context-forge-2 --tail 50 | grep -i "cost"
```

Look for:
```
✅ CostAnalysisPlugin initialized - Daily budget: $100, Monthly budget: $3000
```

## 📊 Test It

Make a test API call and check for cost metadata:
```bash
curl -X POST https://your-app-url/mcp/tools/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "test", "arguments": {}}' | jq '.metadata.cost_analysis'
```

## 🎯 Default Configuration

- **Daily Budget**: $100
- **Monthly Budget**: $3000
- **Per-User Daily**: $10
- **Warning Alert**: 75%
- **Critical Alert**: 90%
- **Block on Exceeded**: No (warnings only)

## 📝 Customize Before Upload

Edit `plugins/config_cost_analysis_cos.yaml` to adjust:
- Budget limits
- Pricing (match your LLM provider)
- Alert thresholds
- Request blocking behavior

## 📚 Full Documentation

See `COST_ANALYSIS_COS_UPLOAD.md` for:
- Alternative upload methods (AWS CLI, Python)
- Detailed configuration options
- Troubleshooting guide
- Monitoring and metrics

---

**Made with Bob** 🤖