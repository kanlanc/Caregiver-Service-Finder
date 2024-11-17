import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry
from firecrawl import FireCrawler  # Placeholder import
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS
allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
CORS(app, origins=allowed_origins)

# Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
RATE_LIMIT = int(os.getenv('RATE_LIMIT', 100))
CRAWLER_TIMEOUT = int(os.getenv('CRAWLER_TIMEOUT', 30))

# Initialize FireCrawler (placeholder)
crawler = FireCrawler()

def get_crawler():
    """
    Factory function to get crawler instance
    Could be extended to handle multiple crawler instances or configuration
    """
    return FireCrawler()

@sleep_and_retry
@limits(calls=RATE_LIMIT, period=60)
def rate_limited_crawler(url):
    """Rate limited crawler function"""
    crawler = get_crawler()
    # Add actual crawling logic here
    return {"url": url, "content": f"Crawled content from {url}", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")}

@app.route('/echo', methods=['POST'])
def echo():
    """Simple echo endpoint to test the API"""
    data = request.get_json()
    return jsonify({"message": data.get('text', '')})

@app.route('/crawl', methods=['POST'])
def crawl():
    """Endpoint to crawl websites using firecrawl"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        result = rate_limited_crawler(url)
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error crawling {url}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    })

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors"""
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

if __name__ == '__main__':
    # Get port from environment variable (Heroku sets this automatically)
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)