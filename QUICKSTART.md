# 🚀 Quick Start: Deploy to Azure with Proxy Support

This guide will get your Google Scholar Finder app running on Azure in under 10 minutes!

## **Fastest Method: Use ScraperAPI (Recommended)**

### Step 1: Get ScraperAPI Key (1 minute)
1. Visit https://www.scraperapi.com/signup
2. Sign up (free tier gives 1,000 requests/month)
3. Copy your API key from the dashboard

### Step 2: Deploy to Azure (5 minutes)

#### Option A: Using Azure CLI (Fastest)
```bash
# Login to Azure
az login

# Create and deploy in one command!
az webapp up \
  --resource-group scholar-finder-rg \
  --name google-scholar-finder-$(whoami) \
  --runtime "PYTHON:3.11" \
  --sku B1

# Configure environment variables
az webapp config appsettings set \
  --resource-group scholar-finder-rg \
  --name google-scholar-finder-$(whoami) \
  --settings \
    SCRAPERAPI_KEY="your_scraperapi_key_here" \
    TAVILY_API_KEY="your_tavily_key"

# Set startup command
az webapp config set \
  --resource-group scholar-finder-rg \
  --name google-scholar-finder-$(whoami) \
  --startup-file "python -m streamlit run app_azure.py --server.port=8000 --server.address=0.0.0.0"
```

#### Option B: Using Azure Portal (GUI Method)
1. **Create App Service:**
   - Go to https://portal.azure.com
   - Click "Create a resource" → "Web App"
   - Fill in:
     - Name: `google-scholar-finder-yourname`
     - Runtime: Python 3.11
     - Region: East US (or nearest)
     - Pricing: Basic B1
   - Click "Review + Create"

2. **Deploy Code:**
   ```bash
   # In your project directory
   cd /home/kowshik/personal_work/google-scholar-finder
   
   # Make sure app_azure.py is your main file
   cp app_azure.py app.py
   
   # Deploy using VS Code Azure extension or ZIP deploy
   az webapp deploy \
     --resource-group scholar-finder-rg \
     --name google-scholar-finder-yourname \
     --src-path ./ \
     --type zip
   ```

3. **Configure Settings:**
   - In Azure Portal → Your App Service → Configuration
   - Click "New application setting"
   - Add:
     - Name: `SCRAPERAPI_KEY`, Value: `your_key`
     - Name: `TAVILY_API_KEY`, Value: `your_tavily_key`
   - Click "Save"

4. **Set Startup Command:**
   - In Azure Portal → Your App Service → Configuration → General Settings
   - Startup Command: 
     ```
     python -m streamlit run app_azure.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true
     ```
   - Click "Save"

5. **Restart the App:**
   - Click "Restart" in the Overview page

### Step 3: Test Your App (1 minute)
```bash
# Check if app is running
curl https://google-scholar-finder-yourname.azurewebsites.net/_stcore/health

# Or visit in browser
open https://google-scholar-finder-yourname.azurewebsites.net
```

## **Alternative: Using Docker Container (Azure Container Instances)**

This method is simpler and cheaper for low-traffic applications.

```bash
# Build and push to Azure Container Registry
az acr create \
  --resource-group scholar-finder-rg \
  --name scholarfinderacr \
  --sku Basic

az acr login --name scholarfinderacr

docker build -t scholarfinderacr.azurecr.io/scholar-finder:latest .
docker push scholarfinderacr.azurecr.io/scholar-finder:latest

# Create container instance
az container create \
  --resource-group scholar-finder-rg \
  --name scholar-finder-container \
  --image scholarfinderacr.azurecr.io/scholar-finder:latest \
  --dns-name-label google-scholar-finder \
  --ports 8501 \
  --environment-variables \
    SCRAPERAPI_KEY="your_key" \
    TAVILY_API_KEY="your_tavily_key" \
  --cpu 1 \
  --memory 1.5

# Get the URL
az container show \
  --resource-group scholar-finder-rg \
  --name scholar-finder-container \
  --query ipAddress.fqdn
```

## **Cost Optimization Tips**

### Free Tier Options:
1. **ScraperAPI Free Tier:** 1,000 requests/month
2. **Azure Free Tier:** $200 credit for 30 days
3. **Azure App Service Free (F1):** Limited but sufficient for testing
   ```bash
   # Use F1 tier instead of B1
   az webapp up --sku F1
   ```

### Production Setup (Estimated $20-50/month):
- Azure App Service B1: ~$13/month
- ScraperAPI Hobby: ~$49/month (100k requests)
- **Total: ~$62/month**

### Budget Setup (Estimated $0-20/month):
- Azure Container Instances: ~$0.000012/second (~$31/month if always on)
- ScraperAPI Free: $0 (1k requests/month)
- **Or run only when needed:** Stop container when not in use = ~$0-5/month

## **Environment Variables Reference**

Set these in Azure Configuration:

```bash
# Required
SCRAPERAPI_KEY=your_scraperapi_key

# Optional (for other proxy methods)
SMARTPROXY_USER=your_username
SMARTPROXY_PASS=your_password
BRIGHTDATA_USER=your_username
BRIGHTDATA_PASS=your_password
CUSTOM_PROXIES=http://proxy1:port,http://proxy2:port

# Other settings
TAVILY_API_KEY=your_tavily_key
ENABLE_TOR=false
```

## **Monitoring & Debugging**

### View Logs:
```bash
# Stream logs
az webapp log tail \
  --resource-group scholar-finder-rg \
  --name google-scholar-finder-yourname

# Enable logging
az webapp log config \
  --resource-group scholar-finder-rg \
  --name google-scholar-finder-yourname \
  --application-logging filesystem \
  --level information
```

### Common Issues:

1. **App won't start:**
   - Check startup command in Configuration → General Settings
   - Verify Python version is 3.11
   - Check logs: `az webapp log tail`

2. **Proxy not working:**
   - Verify environment variables are set
   - Check if SCRAPERAPI_KEY is correct
   - Test locally first: `export SCRAPERAPI_KEY=xxx && streamlit run app_azure.py`

3. **Slow performance:**
   - Upgrade to B2 or S1 tier
   - Enable Application Insights for monitoring
   - Consider using Azure CDN

## **Next Steps**

1. **Enable CI/CD:** The GitHub Actions workflow is ready in `.github/workflows/azure-deploy.yml`
2. **Custom Domain:** Add your domain in Azure Portal → Custom domains
3. **SSL Certificate:** Free with Azure App Service
4. **Monitoring:** Enable Application Insights for performance tracking

## **Support & Resources**

- **ScraperAPI Docs:** https://www.scraperapi.com/documentation/
- **Azure App Service Docs:** https://docs.microsoft.com/azure/app-service/
- **Streamlit on Azure:** https://docs.streamlit.io/knowledge-base/tutorials/deploy/azure

---

**Total Setup Time:** ~10 minutes  
**Monthly Cost:** $0-62 depending on usage  
**Reliability:** 99.95% uptime with Azure SLA
