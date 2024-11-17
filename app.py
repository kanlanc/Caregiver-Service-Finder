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

# Configure app
app.config['FIRECRAWL_SECRET_KEY'] = os.getenv('FIRECRAWL_SECRET_KEY', 'default-secret-key')
app.config['TOGETHER_SECRET_KEY'] = os.getenv('TOGETHER_SECRET_KEY', 'default-secret-key')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN', 'default-secret-key')

bot = telebot.TeleBot(bot_token, threaded=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



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
    webhook_url = f'https://ibmhack-46f00826304f.herokuapp.com/webhook/{bot.token}'
    logger.info(f"Setting webhook to: {webhook_url}")
    
    try:
        bot.remove_webhook()
        response = bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set response: {response}")
        return f"Webhook set to {webhook_url}"
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return f"Failed to set webhook: {str(e)}", 500

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I'm your bot.")

