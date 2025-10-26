# Azure Deployment Guide for Google Scholar Finder with Proxy

This guide explains how to deploy your Google Scholar application on Azure with proxy support to avoid blocking issues.

## **Solution Overview**

You have 3 main options:

### **Option 1: Use Third-Party Proxy Service (Recommended - Easiest)**
Use a managed proxy service like ScraperAPI, SmartProxy, or BrightData.

**Pros:**
- No infrastructure management
- Automatic IP rotation
- CAPTCHA handling
- High success rate

**Cons:**
- Monthly cost ($20-100/month)

**Best for:** Production applications, minimal setup time

### **Option 2: Deploy Your Own Proxy Server on Azure**
Deploy the included `simple_proxy_server.py` as a separate Azure App Service.

**Pros:**
- Full control
- Lower cost for high volume
- No third-party dependencies

**Cons:**
- Still might get blocked by Google Scholar
- Requires more setup

**Best for:** Budget-conscious projects, learning

### **Option 3: Use Azure NAT Gateway with Multiple IPs**
Use Azure's NAT Gateway with multiple public IPs for IP rotation.

**Pros:**
- Native Azure solution
- Reliable and fast
- Good for moderate usage

**Cons:**
- Azure infrastructure costs
- Requires VNet setup

**Best for:** Enterprise applications, compliance requirements

---

## **Implementation Guide**

### **Option 1: Using ScraperAPI (Recommended)**

#### Step 1: Get API Key
1. Sign up at https://www.scraperapi.com/
2. Get your API key (free tier: 1,000 requests/month)

#### Step 2: Configure Environment Variables in Azure
```bash
# In Azure Portal > App Service > Configuration > Application Settings
SCRAPERAPI_KEY=your_api_key_here
```

#### Step 3: Update your app.py
The app already supports this - just set the environment variable!

---

### **Option 2: Deploy Your Own Proxy Server**

#### Step 1: Create a new Azure App Service for the proxy
```bash
# Login to Azure
az login

# Create resource group (if not exists)
az group create --name scholar-proxy-rg --location eastus

# Create App Service Plan (Linux)
az appservice plan create \
  --name scholar-proxy-plan \
  --resource-group scholar-proxy-rg \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group scholar-proxy-rg \
  --plan scholar-proxy-plan \
  --name scholar-proxy-server \
  --runtime "PYTHON:3.11"
```

#### Step 2: Deploy the proxy server
```bash
# Navigate to your project directory
cd /home/kowshik/personal_work/google-scholar-finder

# Create a separate folder for proxy server
mkdir proxy_server
cp simple_proxy_server.py proxy_server/app.py
cp proxy_server_requirements.txt proxy_server/requirements.txt

# Deploy to Azure
cd proxy_server
az webapp up \
  --resource-group scholar-proxy-rg \
  --name scholar-proxy-server \
  --runtime "PYTHON:3.11"
```

#### Step 3: Use the proxy in your main app
Update your main app to use this proxy:
```python
# In app.py, modify requests to use your proxy
proxy_url = "https://scholar-proxy-server.azurewebsites.net/proxy"
response = requests.get(f"{proxy_url}?url={target_url}")
```

---

### **Option 3: Azure NAT Gateway Setup**

#### Step 1: Create Virtual Network
```bash
# Create VNet
az network vnet create \
  --resource-group scholar-proxy-rg \
  --name scholar-vnet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name scholar-subnet \
  --subnet-prefix 10.0.1.0/24
```

#### Step 2: Create Public IPs (multiple for rotation)
```bash
# Create multiple public IPs
for i in {1..3}; do
  az network public-ip create \
    --resource-group scholar-proxy-rg \
    --name scholar-public-ip-$i \
    --sku Standard \
    --allocation-method Static
done
```

#### Step 3: Create NAT Gateway
```bash
# Create NAT Gateway
az network nat gateway create \
  --resource-group scholar-proxy-rg \
  --name scholar-nat-gateway \
  --public-ip-addresses scholar-public-ip-1 scholar-public-ip-2 scholar-public-ip-3 \
  --idle-timeout 10

# Associate with subnet
az network vnet subnet update \
  --resource-group scholar-proxy-rg \
  --vnet-name scholar-vnet \
  --name scholar-subnet \
  --nat-gateway scholar-nat-gateway
```

#### Step 4: Deploy App Service with VNet Integration
```bash
# Create App Service with VNet integration
az webapp create \
  --resource-group scholar-proxy-rg \
  --plan scholar-proxy-plan \
  --name google-scholar-finder \
  --runtime "PYTHON:3.11"

# Enable VNet integration
az webapp vnet-integration add \
  --resource-group scholar-proxy-rg \
  --name google-scholar-finder \
  --vnet scholar-vnet \
  --subnet scholar-subnet
```

---

## **Best Practices for Azure Deployment**

### 1. **Use Azure Key Vault for Secrets**
```bash
# Create Key Vault
az keyvault create \
  --name scholar-keyvault \
  --resource-group scholar-proxy-rg \
  --location eastus

# Store secrets
az keyvault secret set \
  --vault-name scholar-keyvault \
  --name scraperapi-key \
  --value "your_api_key"

# Enable managed identity for App Service
az webapp identity assign \
  --resource-group scholar-proxy-rg \
  --name google-scholar-finder

# Grant access to Key Vault
az keyvault set-policy \
  --name scholar-keyvault \
  --object-id <app-service-principal-id> \
  --secret-permissions get list
```

### 2. **Enable Application Insights**
```bash
az monitor app-insights component create \
  --app scholar-insights \
  --location eastus \
  --resource-group scholar-proxy-rg
```

### 3. **Configure Auto-scaling**
```bash
az monitor autoscale create \
  --resource-group scholar-proxy-rg \
  --resource google-scholar-finder \
  --resource-type Microsoft.Web/sites \
  --name autoscale-settings \
  --min-count 1 \
  --max-count 3 \
  --count 1
```

### 4. **Set up CI/CD with GitHub Actions**
Create `.github/workflows/azure-deploy.yml` (see file in project)

---

## **Cost Estimation**

### **Option 1: ScraperAPI**
- Free tier: 1,000 requests/month
- Hobby: $49/month for 100,000 requests
- Business: $149/month for 500,000 requests

### **Option 2: Self-hosted Proxy**
- App Service (B1): ~$13/month
- Likely to get blocked, may need multiple instances

### **Option 3: NAT Gateway**
- NAT Gateway: ~$32/month
- Public IPs: ~$3/IP/month × 3 = $9/month
- App Service (B1): ~$13/month
- **Total: ~$54/month**

---

## **Recommended Approach**

For your use case, I recommend:

1. **Start with ScraperAPI** (Option 1) - free tier to test
2. If you exceed free tier and want to save costs, implement **Option 3** (Azure NAT Gateway)
3. Option 2 (self-hosted proxy) is only useful as a learning exercise

---

## **Quick Start Commands**

```bash
# Clone and setup
cd /home/kowshik/personal_work/google-scholar-finder

# Set environment variable for ScraperAPI
export SCRAPERAPI_KEY="your_key_here"

# Test locally
streamlit run app.py

# Deploy to Azure (after updating app.py)
az webapp up \
  --resource-group scholar-proxy-rg \
  --name google-scholar-finder \
  --runtime "PYTHON:3.11"

# Configure environment variables in Azure
az webapp config appsettings set \
  --resource-group scholar-proxy-rg \
  --name google-scholar-finder \
  --settings SCRAPERAPI_KEY="your_key_here"
```

---

## **Monitoring and Troubleshooting**

### View logs
```bash
az webapp log tail \
  --resource-group scholar-proxy-rg \
  --name google-scholar-finder
```

### Check health
```bash
curl https://google-scholar-finder.azurewebsites.net
```

### Restart app
```bash
az webapp restart \
  --resource-group scholar-proxy-rg \
  --name google-scholar-finder
```
