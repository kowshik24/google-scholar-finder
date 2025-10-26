#!/usr/bin/env python3
"""
Alternative Azure Deployment using GitHub Actions
Since Azure CLI installation is having issues, we'll set up GitHub Actions for deployment
"""

import os
import subprocess

print("="*70)
print("ALTERNATIVE DEPLOYMENT METHOD: GitHub Actions")
print("="*70)

print("""
Since Azure CLI installation is having issues, here are your options:

OPTION 1: Deploy via Azure Portal (Easiest - No CLI needed!)
============================================================
1. Go to: https://portal.azure.com
2. Click "Create a resource" → Search "Web App"
3. Fill in the form:
   - Name: google-scholar-finder-kowshik
   - Runtime: Python 3.11
   - Region: East US (or nearest)
   - Pricing: Basic B1 (or Free F1 for testing)
4. Click "Review + Create" → "Create"
5. Once created, go to your Web App
6. In the left menu: Deployment → Deployment Center
7. Choose: GitHub
8. Authorize and select:
   - Organization: kowshik24
   - Repository: google-scholar-finder
   - Branch: main
9. Azure will create GitHub Actions workflow automatically!
10. Go to Configuration → Application Settings
11. Add: SCRAPERAPI_KEY = ba32df0ed6069c2277a6dd94ae4579c1
12. Go to Configuration → General Settings
13. Startup Command: python -m streamlit run app_azure.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true
14. Save and restart!

✅ Your app will be live at: https://google-scholar-finder-kowshik.azurewebsites.net


OPTION 2: Deploy via GitHub Actions (Best for CI/CD)
====================================================
1. Push your code to GitHub (if not already)
2. Go to: https://portal.azure.com
3. Create a Web App (same as Option 1, steps 1-4)
4. Download the publish profile:
   - In your Web App → Deployment → Deployment Center
   - Click "Manage publish profile" → Download
5. Add to GitHub Secrets:
   - Go to: https://github.com/kowshik24/google-scholar-finder/settings/secrets/actions
   - Click "New repository secret"
   - Name: AZURE_WEBAPP_PUBLISH_PROFILE
   - Value: Paste the downloaded publish profile content
6. Add another secret:
   - Name: SCRAPERAPI_KEY
   - Value: ba32df0ed6069c2277a6dd94ae4579c1
7. The GitHub Actions workflow is already set up (.github/workflows/azure-deploy.yml)
8. Push to main branch → Auto deploys!


OPTION 3: Deploy via Docker to Azure Container Instances
========================================================
1. Go to: https://portal.azure.com
2. Create "Container Instances"
3. Use the Docker image or public registry
4. Set environment variable: SCRAPERAPI_KEY=ba32df0ed6069c2277a6dd94ae4579c1
5. Open port 8501


OPTION 4: Use Azure Cloud Shell (No local CLI needed!)
======================================================
1. Go to: https://portal.azure.com
2. Click the Cloud Shell icon (>_) at the top
3. Choose Bash
4. Run these commands in Cloud Shell:

# Clone your repo
git clone https://github.com/kowshik24/google-scholar-finder.git
cd google-scholar-finder

# Deploy
az webapp up \\
  --name google-scholar-finder-kowshik \\
  --runtime "PYTHON:3.11" \\
  --sku B1 \\
  --location eastus \\
  --resource-group scholar-finder-rg

# Configure
az webapp config appsettings set \\
  --resource-group scholar-finder-rg \\
  --name google-scholar-finder-kowshik \\
  --settings SCRAPERAPI_KEY="ba32df0ed6069c2277a6dd94ae4579c1"

az webapp config set \\
  --resource-group scholar-finder-rg \\
  --name google-scholar-finder-kowshik \\
  --startup-file "python -m streamlit run app_azure.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true"


RECOMMENDED: Option 1 or Option 4
==================================
- Option 1 is easiest (GUI only, no commands)
- Option 4 is fastest (Cloud Shell has Azure CLI pre-installed)

Both will get your app live in under 10 minutes!
""")

print("\n" + "="*70)
print("NEXT STEPS:")
print("="*70)
print("1. Choose one of the options above")
print("2. Follow the step-by-step instructions")
print("3. Your app will be live!")
print("\nYour ScraperAPI key is already tested and working!")
print("="*70)
