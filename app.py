import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from together import Together
import time
import telebot
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS to allow all origins
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure app
app.config['FIRECRAWL_SECRET_KEY'] = os.getenv('FIRECRAWL_SECRET_KEY', 'default-secret-key')
app.config['TOGETHER_SECRET_KEY'] = os.getenv('TOGETHER_SECRET_KEY', 'default-secret-key')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN', 'default-secret-key')

# Add validation for bot token
if bot_token == 'default-secret-key':
    logger.error("No Telegram bot token provided! Bot functionality will not work.")
    bot = None
else:
    bot = telebot.TeleBot(bot_token, threaded=False)
    logger.info("Telegram bot initialized")





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
            messages=[{"role": "system", "content": system_prompt},  {"role": "user", "content": "The requirements are: " + requirements+"\n\nThe output should be a list of people that match the requirements in a list format. Remove all information except contact information, relevant experience condensed down to 1 line and the cost for the service."}]
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


@app.route('/scrape_grant_info', methods=['POST'])
def scrape_grant_info():
    """Endpoint to scrape and process grant-related information"""
    data = request.get_json()
    grant_url = data.get('url')
    
    if not grant_url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        # Scrape the grant webpage
        result = crawler.scrape_url(grant_url, params={'formats': ['markdown']})
        
        # Truncate the content to roughly 6000 tokens (approximately 8000 characters)
        # This leaves room for the system prompt and other overhead
        content = result['markdown'][:8000] + "..." if len(result['markdown']) > 8000 else result['markdown']
        
        # Process the content using Together API
        system_prompt = """You are a grant analysis expert. Given the content from a grant-related webpage, 
        extract and organize the following key information:
        1. Eligibility requirements
        2. Funding amounts
        3. Key deadlines
        4. Required documentation
        5. Priority areas
        Please format the response as a structured list."""
        
        together_response = together.chat.completions.create(
            model="meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
        )
        
        return jsonify({
            "analysis": together_response.choices[0].message.content,
            "raw_content": content,
            "truncated": len(content) < len(result['markdown'])
        })
        
    except Exception as e:
        app.logger.error(f"Error processing grant information: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/generate_nsf_grant', methods=['POST'])
def generate_nsf_grant():
    """Endpoint to generate NSF grant draft"""
    data = request.get_json()
    required_fields = ['project_title', 'research_objectives', 'methodology', 'budget', 'timeline']
    
    # Validate input
    if not all(field in data for field in required_fields):
        return jsonify({
            "error": f"Missing required fields. Please provide: {', '.join(required_fields)}"
        }), 400
    
    try:
        system_prompt = """You are an experienced NSF grant writer. Using the provided information, 
        create a comprehensive draft of an NSF grant proposal following standard NSF formatting and requirements. 
        Include sections for:
        - Project Summary
        - Project Description
        - Research Objectives
        - Methodology
        - Expected Outcomes
        - Broader Impacts
        - Budget Justification
        - Timeline
        Make sure to maintain NSF's technical writing style and focus on scientific merit and broader impacts."""
        
        user_content = f"""
        Project Title: {data['project_title']}
        Research Objectives: {data['research_objectives']}
        Methodology: {data['methodology']}
        Budget: {data['budget']}
        Timeline: {data['timeline']}
        """
        
        together_response = together.chat.completions.create(
            model="meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        return jsonify({
            "grant_draft": together_response.choices[0].message.content
        })
        
    except Exception as e:
        app.logger.error(f"Error generating NSF grant draft: {str(e)}")
        return jsonify({"error": str(e)}), 500




@app.route(f'/webhook/{bot.token}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return jsonify({'ok': True})
    else:
        return jsonify({'ok': False, 'error': 'Invalid content type'}), 400

@app.route('/set_webhook')
def set_webhook():
    if not bot:
        return "Bot not initialized - check TELEGRAM_BOT_TOKEN", 500
        
    webhook_url = f'https://ibmhack-46f00826304f.herokuapp.com/webhook/{bot.token}'
    logger.info(f"Setting webhook to: {webhook_url}")
    
    try:
        bot.remove_webhook()
        time.sleep(0.1)  # Small delay to ensure webhook is removed
        response = bot.set_webhook(url=webhook_url)
        if response:
            logger.info("Webhook set successfully")
            return f"Webhook set to {webhook_url}"
        else:
            logger.error("Failed to set webhook")
            return "Failed to set webhook", 500
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return f"Failed to set webhook: {str(e)}", 500

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I'm your bot.")

@app.route('/')
def root():
    """Root endpoint"""
    return jsonify({
        "status": "running",
        "endpoints": [
            "/health",
            "/echo",
            "/findpeople",
            "/set_webhook",
            "/scrape_grant_info",
            "/generate_nsf_grant"
        ]
    })

@app.route('/favicon.ico')
def favicon():
    """Favicon endpoint"""
    return '', 204  # Return empty response with "No Content" status


if __name__ == "__main__":
    # Add webhook setup on startup
    if bot:
        with app.app_context():
            logger.info("Setting up webhook on startup...")
            set_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))