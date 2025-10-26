"""
Simple HTTP Proxy Server to deploy on Azure
This can be deployed as a separate Azure App Service or Azure Container Instance
"""

from flask import Flask, request, Response
import requests
import random
import time
from datetime import datetime
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

# Rate limiting
request_times = []
MAX_REQUESTS_PER_MINUTE = 10

def check_rate_limit():
    """Simple rate limiting"""
    global request_times
    now = datetime.now()
    
    # Remove requests older than 1 minute
    request_times = [t for t in request_times if (now - t).total_seconds() < 60]
    
    if len(request_times) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    request_times.append(now)
    return True

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    """
    Proxy endpoint that forwards requests to target URL
    Usage: http://your-proxy.azurewebsites.net/proxy?url=https://scholar.google.com/...
    """
    
    # Check rate limit
    if not check_rate_limit():
        return Response('Rate limit exceeded. Please try again later.', status=429)
    
    # Get target URL from query parameter
    target_url = request.args.get('url')
    
    if not target_url:
        return Response('Missing URL parameter', status=400)
    
    # Validate URL (basic security)
    if not target_url.startswith(('http://', 'https://')):
        return Response('Invalid URL', status=400)
    
    try:
        # Random delay to avoid detection
        time.sleep(random.uniform(1, 3))
        
        # Prepare headers with rotation
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        # Forward the request
        if request.method == 'GET':
            response = requests.get(
                target_url,
                headers=headers,
                timeout=30,
                allow_redirects=True
            )
        else:
            response = requests.post(
                target_url,
                headers=headers,
                data=request.get_data(),
                timeout=30,
                allow_redirects=True
            )
        
        # Log the request
        logger.info(f"Proxied request to {target_url} - Status: {response.status_code}")
        
        # Return the response
        return Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )
        
    except requests.RequestException as e:
        logger.error(f"Proxy request failed: {e}")
        return Response(f'Proxy request failed: {str(e)}', status=500)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Azure"""
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with usage instructions"""
    return '''
    <html>
        <head><title>Simple Proxy Server</title></head>
        <body>
            <h1>Simple Proxy Server</h1>
            <p>This is a simple proxy server for making HTTP requests.</p>
            <h2>Usage:</h2>
            <code>GET /proxy?url=https://example.com</code>
            <h2>Health Check:</h2>
            <code>GET /health</code>
            <p>Rate Limit: 10 requests per minute</p>
        </body>
    </html>
    '''

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
