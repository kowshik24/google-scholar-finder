# Bright Data (Luminati) Proxy Setup Guide

This guide explains how to use Bright Data (formerly Luminati) proxies with the Google Scholar scraper.

## Quick Start

### Option 1: Direct Connection (Simplest)

1. Sign up at [Bright Data](https://brightdata.com/)
2. Create a residential zone in your dashboard
3. Update `.env`:
   ```env
   CONNECTION_METHOD=luminati
   BRIGHTDATA_USERNAME=your_customer_id
   BRIGHTDATA_PASSWORD=your_zone_password
   BRIGHTDATA_ZONE=residential
   ```
4. Run the scraper:
   ```bash
   python google_scholar_scrapper_scholarly.py
   ```

### Option 2: Docker with Proxy Manager (Advanced)

Run the Luminati Proxy Manager locally for better control, caching, and IP rotation.

1. Get your API token from Bright Data dashboard
2. Update `.env`:
   ```env
   CONNECTION_METHOD=luminati_local
   BRIGHTDATA_TOKEN=your_api_token
   ```
3. Start services:
   ```bash
   docker-compose up -d
   ```
4. Access Proxy Manager UI at http://localhost:22999
5. Configure your proxy zones in the UI

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONNECTION_METHOD` | Proxy method to use | `none` |
| `BRIGHTDATA_USERNAME` | Your Bright Data customer ID | - |
| `BRIGHTDATA_PASSWORD` | Zone password | - |
| `BRIGHTDATA_ZONE` | Zone name (residential, datacenter, isp) | `residential` |
| `BRIGHTDATA_COUNTRY` | Target country code (us, uk, de, etc.) | - |
| `BRIGHTDATA_TOKEN` | API token for Proxy Manager | - |
| `BRIGHTDATA_HOST` | Super proxy hostname | `brd.superproxy.io` |
| `BRIGHTDATA_PORT` | Super proxy port | `22225` |

### Connection Methods

- **`luminati`**: Direct connection to Bright Data's super proxy
- **`luminati_local`**: Connect via local Luminati Proxy Manager (docker-compose)
- **`scraperapi`**: Use ScraperAPI as alternative
- **`freeproxy`**: Use free proxies (unreliable)
- **`none`**: No proxy

## Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f luminati-proxy

# Stop services
docker-compose down

# Restart proxy manager
docker-compose restart luminati-proxy
```

## Proxy Manager Ports

| Port | Purpose |
|------|---------|
| 22999 | Web UI / Admin panel |
| 22225 | Dropin proxy (direct replacement for super-proxy) |
| 24000 | First configurable proxy port |

## Finding Your Credentials

1. Log in to [Bright Data Dashboard](https://brightdata.com/cp)
2. **Customer ID**: Found in account settings or use your login email
3. **Zone Password**: Go to Proxies → Select Zone → Zone Settings → API Credentials
4. **API Token**: Account Settings → API Token

## Residential vs Datacenter Proxies

| Type | Best For | Cost |
|------|----------|------|
| Residential | Google Scholar (recommended) | Higher |
| Datacenter | High-volume, less detection-sensitive | Lower |
| ISP | Balance of both | Medium |

## Troubleshooting

### "Proxy authentication failed"
- Verify your username format: `brd-customer-{CUSTOMER_ID}-zone-{ZONE}`
- Check zone password is correct
- Ensure zone is active in dashboard

### "Connection refused"
- For `luminati_local`: Ensure Proxy Manager container is running
- Check firewall isn't blocking ports 22225, 22999

### "IP blocked by Google Scholar"
- Try adding country targeting: `BRIGHTDATA_COUNTRY=us`
- Enable IP rotation in Proxy Manager
- Use residential IPs instead of datacenter

### Rate limiting
- Add delays between requests (already implemented in scraper)
- Use session persistence for same author queries
- Configure retry rules in Proxy Manager

## Example: Full Docker Setup

```bash
# 1. Clone and navigate to project
cd google-scholar-finder

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Start services
docker-compose up -d

# 4. Wait for Proxy Manager to initialize
docker-compose logs -f luminati-proxy

# 5. Access Proxy Manager UI
open http://localhost:22999

# 6. Run scraper (in container or locally)
docker-compose exec scholar-scraper python google_scholar_scrapper_scholarly.py
```

## Additional Resources

- [Bright Data Documentation](https://brightdata.com/docs)
- [Proxy Manager GitHub](https://github.com/luminati-io/luminati-proxy)
- [scholarly Library](https://github.com/scholarly-python-package/scholarly)
