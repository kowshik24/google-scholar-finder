# 📚 Google Scholar Finder - Azure Edition

A Streamlit application to fetch and display academic publications from Google Scholar with **Azure-optimized proxy support** to avoid blocking issues.

## 🌟 Features

- ✅ Fetch papers by Google Scholar author ID
- ✅ Filter by date range
- ✅ **Multiple proxy strategies** for reliable scraping
- ✅ **Azure-optimized** deployment configurations
- ✅ Fallback methods when primary API fails
- ✅ Export functionality for all papers
- ✅ Citation counts and author information
- ✅ Production-ready with monitoring support

## 🚀 Quick Deploy to Azure

**Fastest method (5 minutes):**

```bash
# 1. Get ScraperAPI key (free tier): https://www.scraperapi.com/signup

# 2. Deploy to Azure
az login
az webapp up --name google-scholar-finder-$(whoami) --runtime "PYTHON:3.11" --sku B1

# 3. Configure proxy
az webapp config appsettings set \
  --name google-scholar-finder-$(whoami) \
  --settings SCRAPERAPI_KEY="your_key_here"

# 4. Set startup command
az webapp config set \
  --name google-scholar-finder-$(whoami) \
  --startup-file "python -m streamlit run app_azure.py --server.port=8000 --server.address=0.0.0.0"

# Done! Visit https://google-scholar-finder-yourname.azurewebsites.net
```

See **[QUICKSTART.md](QUICKSTART.md)** for detailed instructions.

## 📋 Proxy Solutions for Azure

This app supports **multiple proxy strategies** to prevent Google Scholar from blocking your requests:

### 1. **ScraperAPI** (Recommended)
- ✅ Automatic IP rotation
- ✅ CAPTCHA solving
- ✅ 99.9% uptime
- ✅ Free tier: 1,000 requests/month
- 💰 Paid: $49/month for 100k requests

**Setup:**
```bash
export SCRAPERAPI_KEY="your_key"
```

### 2. **SmartProxy**
- ✅ Residential proxies
- ✅ 40M+ IP pool
- 💰 $75/month for 5GB

**Setup:**
```bash
export SMARTPROXY_USER="your_username"
export SMARTPROXY_PASS="your_password"
```

### 3. **BrightData (Luminati)**
- ✅ Enterprise-grade
- ✅ Largest proxy network
- 💰 Custom pricing

**Setup:**
```bash
export BRIGHTDATA_USER="your_username"
export BRIGHTDATA_PASS="your_password"
```

### 4. **Custom Proxy Server** (DIY)
- ✅ Full control
- ✅ Can deploy on Azure
- ⚠️ May still get blocked

**Setup:**
```bash
# Deploy simple_proxy_server.py to Azure
# Then use it:
export CUSTOM_PROXIES="http://your-proxy.azurewebsites.net:8000"
```

### 5. **Azure NAT Gateway** (Advanced)
- ✅ Native Azure solution
- ✅ Multiple static IPs
- 💰 ~$54/month

See **[AZURE_DEPLOYMENT_GUIDE.md](AZURE_DEPLOYMENT_GUIDE.md)** for full setup.

## 📦 Installation

### Local Development

```bash
# Clone the repository
git clone https://github.com/kowshik24/google-scholar-finder.git
cd google-scholar-finder

# Install dependencies
pip install -r requirements.txt

# Set up proxy (optional but recommended)
export SCRAPERAPI_KEY="your_key"

# Run the app
streamlit run app_azure.py
```

### Docker

```bash
# Build
docker build -t google-scholar-finder .

# Run
docker run -p 8501:8501 \
  -e SCRAPERAPI_KEY="your_key" \
  google-scholar-finder
```

## 🔧 Configuration

### Environment Variables

Set these in Azure App Service Configuration or locally:

| Variable | Description | Required |
|----------|-------------|----------|
| `SCRAPERAPI_KEY` | ScraperAPI API key | Recommended |
| `SMARTPROXY_USER` | SmartProxy username | Optional |
| `SMARTPROXY_PASS` | SmartProxy password | Optional |
| `BRIGHTDATA_USER` | BrightData username | Optional |
| `BRIGHTDATA_PASS` | BrightData password | Optional |
| `CUSTOM_PROXIES` | Comma-separated proxy URLs | Optional |
| `TAVILY_API_KEY` | Tavily API key | Optional |

### Azure App Service Settings

1. **Runtime:** Python 3.11
2. **Startup Command:**
   ```
   python -m streamlit run app_azure.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true
   ```
3. **Port:** 8000
4. **Always On:** Enabled (for B1 and above)

## 📊 Usage

1. **Enter Google Scholar Author ID**
   - Find it in the URL: `https://scholar.google.com/citations?user=AUTHOR_ID`
   - Example: For Stephen Hawking, the ID is `qc6CJjYAAAAJ`

2. **Set Date Range**
   - Start Year: e.g., 2020
   - End Year: e.g., 2025

3. **Choose Fetch Method**
   - Scholarly Library (tries API first)
   - Web Scraping Only (more reliable)

4. **Click "Fetch Papers"**

5. **Export Results**
   - Copy all papers from the text area
   - Or expand individual papers for details

## 🏗️ Architecture

```
┌─────────────────┐
│   Streamlit UI  │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Azure App Service  │
│   (Python 3.11)     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Proxy Manager      │
│  (azure_proxy_      │
│   config.py)        │
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────────┐
│ScraperAPI│ │Google Scholar│
└──────────┘ └──────────────┘
```

## 📁 Project Structure

```
google-scholar-finder/
├── app.py                          # Original app
├── app_azure.py                    # Azure-optimized app ⭐
├── azure_proxy_config.py           # Proxy management ⭐
├── simple_proxy_server.py          # DIY proxy server
├── requirements.txt                # Python dependencies
├── proxy_server_requirements.txt   # Proxy server deps
├── Dockerfile                      # Container deployment
├── startup.txt                     # Azure startup command
├── .github/workflows/
│   └── azure-deploy.yml           # CI/CD pipeline
├── QUICKSTART.md                  # Quick start guide ⭐
├── AZURE_DEPLOYMENT_GUIDE.md      # Full deployment docs ⭐
└── README.md                      # This file
```

## 💰 Cost Estimation

### Development/Testing
- **Azure App Service (F1 Free):** $0/month
- **ScraperAPI Free Tier:** $0/month (1k requests)
- **Total: $0/month**

### Production (Low Volume)
- **Azure App Service (B1):** $13/month
- **ScraperAPI Hobby:** $49/month (100k requests)
- **Total: $62/month**

### Production (High Volume)
- **Azure App Service (S1):** $70/month
- **BrightData Custom:** $500+/month
- **Azure Application Insights:** $2.88/GB
- **Total: $570+/month**

## 🔍 Troubleshooting

### Issue: "NoneType object has no attribute 'get'"
**Solution:** This is a scholarly library issue. Click "Clear Cache" and try again. The app will automatically fall back to web scraping.

### Issue: Rate Limiting / Blocked by Google Scholar
**Solution:** 
1. Set up ScraperAPI (recommended)
2. Wait 5-10 minutes between requests
3. Use the web scraping method instead

### Issue: App won't start on Azure
**Solution:**
1. Check startup command in Azure Configuration
2. Verify runtime is Python 3.11
3. Check logs: `az webapp log tail --name your-app-name`

### Issue: Proxy not working
**Solution:**
1. Verify environment variables are set correctly
2. Test ScraperAPI key at https://www.scraperapi.com/dashboard
3. Check app logs for proxy initialization messages

## 📈 Monitoring

### Enable Application Insights
```bash
az monitor app-insights component create \
  --app scholar-insights \
  --location eastus \
  --resource-group scholar-finder-rg

# Get instrumentation key and add to app settings
az webapp config appsettings set \
  --name your-app-name \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="your-key"
```

### View Metrics
- Azure Portal → Your App Service → Monitoring → Metrics
- Track: Request count, Response time, HTTP errors

## 🔐 Security

- **API Keys:** Store in Azure Key Vault (recommended) or App Service Configuration
- **HTTPS:** Enabled by default on Azure App Service
- **Authentication:** Add Azure AD if needed
- **Rate Limiting:** Implemented in custom proxy server

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test on Azure
4. Submit a pull request

## 📄 License

MIT License - feel free to use this project commercially or personally.

## 🙏 Acknowledgments

- **scholarly:** Python library for Google Scholar
- **ScraperAPI:** Proxy service provider
- **Streamlit:** Web framework
- **Azure:** Cloud hosting platform

## 📞 Support

- **Issues:** https://github.com/kowshik24/google-scholar-finder/issues
- **Documentation:** See AZURE_DEPLOYMENT_GUIDE.md
- **Quick Start:** See QUICKSTART.md

---

**Made with ❤️ for researchers and academics**

**Deployed on Microsoft Azure** ☁️
