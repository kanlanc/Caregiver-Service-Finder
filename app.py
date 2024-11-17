import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from together import Together
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
    return FirecrawlApp(api_key=app.config['FIRECRAWL_SECRET_KEY'])


def get_together():
    """
    Factory function to get together instance
    """
    return Together(api_key=app.config['TOGETHER_SECRET_KEY'])

# Initialize FireCrawler (placeholder)
crawler = get_crawler()
together = get_together()
@app.route('/echo', methods=['POST'])
def echo():
    """Simple echo endpoint to test the API"""
    data = request.get_json()
    return jsonify({"message": data.get('text', '')})

@app.route('/findpeople', methods=['POST'])
def findpeople():
    """Endpoint to crawl websites using firecrawl"""
    data = request.get_json()
    # url = data.get('url')
    requirements = data.get('requirements')
    # if not url:
    #     return jsonify({"error": "URL is required"}), 400
    
    try:
        # result = crawler.scrape_url(url, params={'formats': ['markdown']})
        result = crawler.scrape_url("https://www.carelinx.com/caregivers/ca/sunnyvale", params={'formats': ['markdown']})
        # print("result:", result)
        # Send the result to the Together API, with a system prompt to summarize the content
        system_prompt = "You are given a list of people and a list of requirements that your looking for, based on the second input that your getting, I want you to match the people that match the input that you are being given in the list of people. The output should be a list of people that match the requirements. The list of people is: " + result['markdown']
        together_response = together.chat.completions.create(
            model="meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
            messages=[{"role": "system", "content": system_prompt},  {"role": "user", "content": "The requirements are: " + requirements+"\n\nThe output should be a list of people that match the requirements in a list format."}]
        )
        

        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error crawling URL: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    })

