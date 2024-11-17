import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS to allow all origins
CORS(app)

# Configure app
app.config['FIRECRAWL_SECRET_KEY'] = os.getenv('FIRECRAWL_SECRET_KEY', 'default-secret-key')
app.config['TOGETHER_SECRET_KEY'] = os.getenv('TOGETHER_SECRET_KEY', 'default-secret-key')




def get_crawler():
    """
    Factory function to get crawler instance
    Could be extended to handle multiple crawler instances or configuration
    """
    return FirecrawlApp()

# Initialize FireCrawler (placeholder)
crawler = get_crawler()

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
        result = crawler.scrape_url(url, params={'formats': ['markdown', 'html']})
        # ADD this to together API and send back the result that your gonna get to client
        
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

