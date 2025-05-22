# slackbot.py
import os
import asyncio
import logging
from dotenv import load_dotenv

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SCRAPE_URLS
from rag_query import RAGQueryProcessor
from scraper import WebScraper
from ingest_to_vector_db import VectorDBManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

print(f"DEBUG: SLACK_BOT_TOKEN loaded: '{os.getenv('SLACK_BOT_TOKEN')}'")
print(f"DEBUG: SLACK_APP_TOKEN loaded: '{os.getenv('SLACK_APP_TOKEN')}'")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

app = App(token=SLACK_BOT_TOKEN)

rag_processor = RAGQueryProcessor()
scraper = WebScraper(SCRAPE_URLS)
db_manager = VectorDBManager()

@app.event("app_mention")
def handle_app_mention(body, say, logger):
    full_text = body["event"]["text"]
    parts = full_text.split(' ', 1)
    user_query = parts[1].strip() if len(parts) > 1 else ""

    logger.info(f"Received app mention: {user_query}")
    if user_query:
        say(f"Hello there! I'm Promo Sensei. Let me process your request: '{user_query}'...")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_text = loop.run_until_complete(asyncio.to_thread(rag_processor.query_llm, user_query))
            say(response_text)
        except Exception as e:
            logger.error(f"Error processing mention: {e}")
            say("Oops! Something went wrong while processing your request.")
    else:
        say("Hello! I'm Promo Sensei. How can I help you today?")


@app.event("message")
def log_all_messages(event, logger):
    logger.info(f"Received message: {event}")


@app.command("/promosensei")
def handle_promosensei_command(ack, respond, command, logger):
    ack()

    text = command["text"].strip()
    logger.info(f"Received slash command: {text}")

    try:
        if text.startswith("search"):
            query = text.replace("search", "", 1).strip()
            if query:
                respond(f"Searching for deals related to '{query}'...")
                # Run sync LLM query
                response_text = rag_processor.query_llm(query)
                respond(response_text)
            else:
                respond("Please provide a search query. Usage: `/promosensei search [your query]`")

        elif text == "summary":
            respond("Generating a summary of top deals...")
            response_text = rag_processor.summarize_top_deals()
            respond(response_text)

        elif text.startswith("brand"):
            brand_name = text.replace("brand", "", 1).strip()
            if brand_name:
                respond(f"Listing offers for brand: '{brand_name}'...")
                response_text = rag_processor.list_offers_by_brand(brand_name)
                respond(response_text)
            else:
                respond("Please provide a brand name. Usage: `/promosensei brand [brand_name]`")

        elif text == "refresh":
            respond("Starting refresh... Please wait a few minutes.")
            try:
                # Scrape synchronously
                scraped_data = asyncio.run(scraper.scrape_all())
                if scraped_data:
                    db_manager.ingest_data(scraped_data)
                    respond(f"Data refreshed! {len(scraped_data)} offers ingested.")
                else:
                    respond("Refresh completed, but no offers were scraped.")
            except Exception as e:
                logger.error(f"Error during refresh: {e}")
                respond("An error occurred during refresh.")
        else:
            respond(
                "Unknown command. Try one of these:\n"
                "`/promosensei search [query]`\n"
                "`/promosensei summary`\n"
                "`/promosensei brand [brand_name]`\n"
                "`/promosensei refresh`"
            )

    except Exception as e:
        logger.error(f"Error in command handler: {e}")
        respond("Something went wrong while processing your command.")

def run_cli_chatbot():
    print("--- Promo Sensei CLI Chatbot ---")
    print("Type your queries or commands. Type 'exit' to quit.")
    print("Commands: search [query], summary, brand [brand_name], refresh")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        if user_input.startswith("search"):
            query = user_input.replace("search", "", 1).strip()
            if query:
                print(f"Promo Sensei: Searching for deals related to '{query}'...")
                response_text = rag_processor.query_llm(query)
                print(f"Promo Sensei: {response_text}")
            else:
                print("Promo Sensei: Please provide a search query. Usage: `search [your query]`")
        elif user_input == "summary":
            print("Promo Sensei: Generating a summary of top deals...")
            response_text = rag_processor.summarize_top_deals()
            print(f"Promo Sensei: {response_text}")
        elif user_input.startswith("brand"):
            brand_name = user_input.replace("brand", "", 1).strip()
            if brand_name:
                print(f"Promo Sensei: Listing offers for brand: '{brand_name}'...")
                response_text = rag_processor.list_offers_by_brand(brand_name)
                print(f"Promo Sensei: {response_text}")
            else:
                print("Promo Sensei: Please provide a brand name. Usage: `brand [brand_name]`")
        elif user_input == "refresh":
            print("Promo Sensei: Initiating data refresh (scraping and ingestion). This may take a few minutes...")
            try:
                scraped_data = asyncio.run(scraper.scrape_all())
                if scraped_data:
                    db_manager.ingest_data(scraped_data)
                    print(f"Promo Sensei: Data refreshed successfully! Ingested {len(scraped_data)} offers.")
                else:
                    print("Promo Sensei: Data refresh completed, but no new offers were scraped.")
            except Exception as e:
                print(f"Promo Sensei: An error occurred during data refresh: {e}")
        else:
            print(
                "Promo Sensei: I didn't understand that command. Here are the available commands:\n"
                "`search [query]` - Find deals based on a user query\n"
                "`summary` - Provide a summary of top deals\n"
                "`brand [brand_name]` - List current offers by a specific brand\n"
                "`refresh` - Trigger the scrape and ingestion cycle"
            )


if __name__ == "__main__":
    if SLACK_BOT_TOKEN and SLACK_APP_TOKEN:
        logging.info("Starting Promo Sensei Slackbot...")
        logging.info("Ensuring initial data is ingested for Slackbot...")
        if not db_manager.metadata_store: # Check if DB is empty
            try:
                logging.info("Database is empty, attempting initial scrape and ingest...")
                loop = asyncio.get_event_loop()
                scraped_data = loop.run_until_complete(scraper.scrape_all())

                if scraped_data:
                    db_manager.ingest_data(scraped_data)
                    logging.info(f"Ingested {len(scraped_data)} offers during startup.")
                else:
                    logging.warning("No offers scraped during initial startup. Bot might have limited functionality.")
            except Exception as e:
                logging.error(f"Error during initial data ingestion for Slackbot: {e}")
                logging.warning("Continuing without initial data. Please use /promosensei refresh to populate.")

        try:
            handler = SocketModeHandler(app, SLACK_APP_TOKEN)
            handler.start()
        except Exception as e:
            logging.critical(f"Failed to start Slack SocketModeHandler: {e}. Falling back to CLI chatbot.")
            run_cli_chatbot() 
    else:
        logging.warning("SLACK_BOT_TOKEN or SLACK_APP_TOKEN not found or are empty. Running CLI chatbot instead.")
        logging.info("Ensuring initial data is ingested for CLI chatbot...")
        if not db_manager.metadata_store: 
            try:
                logging.info("Database is empty, attempting initial scrape and ingest...")
                scraped_data = asyncio.run(scraper.scrape_all())
                if scraped_data:
                    db_manager.ingest_data(scraped_data)
                    logging.info(f"Ingested {len(scraped_data)} offers during startup.")
                else:
                    logging.warning("No offers scraped during initial startup. Chatbot might have limited functionality.")
            except Exception as e:
                logging.error(f"Error during initial data ingestion for CLI chatbot: {e}")
                logging.warning("Continuing without initial data. Use 'refresh' command to populate.")

        run_cli_chatbot()
