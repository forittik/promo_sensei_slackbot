Promo Sensei: Your AI-Powered Promotional Offer Assistant
Promo Sensei is an intelligent system designed to scrape promotional offers from various e-commerce websites, store them in a vector database, and provide an interface (via CLI or Slackbot) to query, summarize, and retrieve these offers using a Large Language Model (LLM) with Retrieval-Augmented Generation (RAG).

Table of Contents
Features

Project Structure

Initial Setup

Prerequisites

API Keys and Environment Variables

Install Dependencies

Configuration (config.py)

How It Works

Web Scraping (scraper.py)

Data Ingestion and Vector Database (ingest_to_vector_db.py)

RAG Query Processing (rag_query.py)

Slackbot Integration (slackbot.py)

Usage

Step 1: Ingest Data

Step 2: Run RAG Queries (CLI)

Step 3: Run the Slackbot

Slackbot Commands

Logging

Future Enhancements

1. Features
Multi-Website Scraping: Gathers promotional offers from popular e-commerce sites like Nykaa, Flipkart, Adidas, Puma, and Amazon.

Intelligent Data Storage: Utilizes a FAISS vector database to store offer embeddings and metadata, enabling efficient semantic search.

Retrieval-Augmented Generation (RAG): Integrates with OpenAI's LLMs to provide context-aware answers to user queries about offers.

Flexible Querying: Supports natural language queries, summarization of top deals, and listing offers by specific brands.

CLI Interface: Allows direct interaction and testing of RAG queries from the command line.

Slackbot Integration: Provides a convenient way to interact with Promo Sensei directly from Slack, making offer information accessible to teams.

Robust URL Cleaning: Automatically cleans Flipkart URLs to remove tracking parameters for cleaner links.

2. Project Structure
promo-sensei/
├── config.py
├── ingest_to_vector_db.py
├── rag_query.py
├── scraper.py
├── slackbot.py
├── .env.example
├── .env (create this file)
└── data/
    ├── faiss_index.bin (generated)
    └── faiss_index_metadata.pkl (generated)

3. Initial Setup
Prerequisites
Python 3.8+

pip (Python package installer)

Access to OpenAI API

A Slack Workspace (if using the Slackbot)

API Keys and Environment Variables
Promo Sensei relies on environment variables for sensitive information like API keys.

Create a .env file: In the root directory of the project, create a file named .env.

Obtain API Keys:

OpenAI API Key:

Go to the OpenAI API website.

Sign in or create an account.

Generate a new secret key.

Copy the key.

Slack Bot Token & App Token (if using Slackbot):

Go to api.slack.com/apps and click "Create New App".

Choose "From an app manifest" and select your workspace.

Use the following manifest (or adapt as needed):

display_information:
  name: Promo Sensei
  description: Your AI-powered promotional offer assistant.
  background_color: "#36C5F0"
features:
  bot_user:
    display_name: Promo Sensei
    always_online: false
  slash_commands:
    - command: /promosensei
      description: Interact with Promo Sensei for offer queries.
      usage_hint: "[query | summary | brand <brand_name> | refresh]"
      should_escape: false
oauth_config:
  scopes:
    bot:
      - commands
      - chat:write
settings:
  event_subscriptions:
    request_url: "" # This will be set by ngrok or your deployment
    bot_events: []
  interactivity:
    is_enabled: true
    request_url: "" # This will be set by ngrok or your deployment
  org_deploy_enabled: false
  socket_mode_enabled: true
  token_rotation_enabled: false

Install the app to your workspace.

Navigate to "Basic Information" -> "Install App" -> "OAuth Tokens for Your Workspace" to find your Bot User OAuth Token (starts with xoxb-). This is SLACK_BOT_TOKEN.

Navigate to "Basic Information" -> "App-Level Tokens" -> "Generate Token and Scopes" to generate an App-Level Token (starts with xapp-). This is SLACK_APP_TOKEN.

Add to .env file:

OPENAI_API_KEY="your_openai_api_key_here"
SLACK_BOT_TOKEN="your_slack_bot_token_here"
SLACK_APP_TOKEN="your_slack_app_token_here"

Replace "your_openai_api_key_here", "your_slack_bot_token_here", and "your_slack_app_token_here" with your actual keys.

Install Dependencies
Navigate to your project's root directory in your terminal and run:

pip install -r requirements.txt
# (Assuming you have a requirements.txt, if not, install manually)
pip install openai faiss-cpu numpy beautifulsoup4 playwright slack_bolt python-dotenv
playwright install
playwright install-deps # For Linux users

4. Configuration (config.py)
The config.py file centralizes all configurable parameters for the application.

OPENAI_API_KEY: Your OpenAI API key (loaded from .env).

SLACK_BOT_TOKEN: Your Slack bot token (loaded from .env).

SLACK_APP_TOKEN: Your Slack app token (loaded from .env).

FAISS_DB_PATH: Path to the FAISS index and metadata files. Default: "data/faiss_index".

LLM_MODEL: The OpenAI model used for RAG queries. Default: "gpt-3.5-turbo".

SCRAPE_URLS: A list of URLs for the scraper to visit. You can enable/disable sites by commenting/uncommenting.

SCRAPE_URLS = [
    "https://www.nykaa.com/sp/offers-native/offers",
    "https://www.flipkart.com/offers-store",
    "https://www.flipkart.com/search?q=beauty+and+cosmetics&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&p%5B%5D=facets.discount_range_v1%255B%255D%3D70%2525%2Bor%2Bmore&p%5B%5D=facets.discount_range_v1%255B%255D%3D60%2525%2Bor%2Bmore&p%5B%5D=facets.discount_range_v1%255B%255D%3D40%2525%2Bor%2Bmore&p%5B%5D=facets.discount_range_v1%255B%255D=50%2525%2Bor%2Bmore",
    "https://www.adidas.co.in/offers",
    "https://in.puma.com/in/en/puma-sale-collection",
    "https://www.amazon.in/deals"
]

Scraper-Specific Limits:

NYKAA_MAX_PAGES = 2: Maximum number of Nykaa pagination pages to scrape. Set to 0 for unlimited (use with caution).

FLIPKART_MAX_PAGES = 2: Maximum number of Flipkart pagination pages (for search results) to scrape. Set to 0 for unlimited.

ADIDAS_MAX_PAGES = 2: Maximum number of Adidas pagination pages to scrape. (Note: Adidas scraping logic in scraper.py currently iterates directly on product cards, so this variable might not be fully utilized for pagination, but it's defined).

MAX_OFFERS_PER_SITE = 5: For Amazon, this limits the number of individual deal pages visited after collecting initial links from the main deals page.

SCRAPE_DELAY_MIN_SECONDS = 1

SCRAPE_DELAY_MAX_SECONDS = 3: These define a random delay between scraping actions to avoid being blocked by websites.

5. How It Works
Web Scraping (scraper.py)
This module is responsible for extracting promotional offer data from specified websites.

Technology: Uses playwright for headless browser automation and BeautifulSoup for HTML parsing.

Supported Sites & Logic:

Nykaa (nykaa.com/sp/offers-native/offers): Navigates to the offers page, clicks a banner to reveal bestsellers, and then iterates through paginated product listings. It extracts product titles, original/offer prices, discounts, and free gift information.

Flipkart Offers Store (flipkart.com/offers-store): Identifies "VIEW ALL" links for different categories on the offers store page. It opens a new browser context/page for each category to scrape product listings (titles, prices, descriptions) from those specific category pages.

Flipkart Search Results (flipkart.com/search): Handles scraping from Flipkart search results pages, including pagination. It extracts product titles, offer/original prices, discounts, ratings, and review counts.

Adidas (adidas.co.in/offers): Scrapes product cards directly from the Adidas offers page, extracting titles, subtitles, colors, current/original prices, campaign info, and links.

Puma (in.puma.com/in/en/puma-sale-collection): Scrapes product tiles, extracting titles, descriptions (price/discount), and offer links.

Amazon Deals (amazon.in/deals): Collects individual deal links from the main Amazon deals page and then visits each deal link to scrape detailed product information (title, price, description, brand) from the individual product pages. It respects MAX_OFFERS_PER_SITE.

Generic Scrape (_generic_scrape): A fallback mechanism that attempts to find common offer-like phrases within the HTML content if site-specific selectors fail. This is less accurate but provides a basic level of extraction.

Expiry Date Parsing (_parse_expiry_date): Tries to extract expiry dates from text using various common date formats and keywords (e.g., "Ends May 23, 2025", "tomorrow").

Data Ingestion and Vector Database (ingest_to_vector_db.py)
This module handles the processing of scraped data and its storage in a FAISS vector database.

Embedding Generation: Uses OpenAI's embedding models (text-embedding-ada-002 by default) to convert textual offer data into numerical vector representations.

FAISS Integration:

faiss_index.bin: Stores the high-dimensional vectors, optimized for fast similarity search.

faiss_index_metadata.pkl: Stores the original offer metadata (title, description, brand, etc.) corresponding to each vector.

Ingestion Process: Takes a list of offer dictionaries, generates embeddings for each, and adds them to the FAISS index along with their metadata.

Search Functionality: Allows searching for offers based on a query string. The query is also embedded, and FAISS finds the most similar offer vectors, returning their associated metadata.

Persistence: The FAISS index and metadata are saved to disk (data/faiss_index.bin and data/faiss_index_metadata.pkl) to persist the database across runs.

RAG Query Processing (rag_query.py)
This module orchestrates the Retrieval-Augmented Generation (RAG) process to answer user queries.

RAG Workflow:

Retrieval: When a user poses a query, it first searches the FAISS vector database (db_manager.search_offers) to retrieve the most semantically relevant promotional offers.

Augmentation: The retrieved offers are then formatted into a structured context string.

Generation: This context, along with the original user query, is sent to an OpenAI LLM (self.llm_client.chat.completions.create) to generate a natural language response.

URL Cleaning: Includes a _clean_flipkart_url helper to remove unnecessary tracking parameters from Flipkart links before presenting them to the LLM or user, ensuring cleaner, more shareable links.

LLM Prompting: Uses a system prompt to define the LLM's persona ("Promo Sensei") and instructs it to answer concisely, prioritize active offers, and format links as Markdown.

Special Commands:

summarize_top_deals(k): Retrieves and summarizes the k most recently ingested offers.

list_offers_by_brand(brand_name): Filters and lists all offers associated with a specific brand from the database.

Slackbot Integration (slackbot.py)
This module enables interaction with Promo Sensei via Slack.

Slack Bolt Framework: Uses the slack_bolt library for building the Slack app.

Socket Mode: Operates in Socket Mode, meaning it doesn't require a public endpoint (like ngrok) for local development, simplifying setup.

Command Handling: Listens for the /promosensei slash command and dispatches to the appropriate RAG query functions based on the command's arguments.

Initial Data Ingestion: On startup, if the FAISS database is empty, it attempts to run the scraper and ingest data. If scraping fails, it falls back to ingesting a set of predefined dummy offers to ensure basic functionality.

CLI Fallback: If Slack tokens are not configured or the Slack connection fails, the bot automatically falls back to a command-line interface (CLI) chatbot for continued testing and interaction.

6. Usage
Step 1: Ingest Data
Before you can query offers, you need to scrape and ingest data into the vector database.

python ingest_to_vector_db.py

This script will:

Initialize the VectorDBManager.

Check if the FAISS database (data/faiss_index.bin and data/faiss_index_metadata.pkl) already exists.

If the database is empty or needs refreshing, it will call the WebScraper to scrape data from the URLs defined in config.py.

It then generates embeddings for the scraped offers and ingests them into the FAISS database.

The database files will be saved in the data/ directory. If you want to force a refresh, delete these files before running the script.

Step 2: Run RAG Queries (CLI)
You can test the RAG query processor directly via the command line.

python rag_query.py

This script will:

Perform an initial data ingestion check (similar to ingest_to_vector_db.py but with a dummy data fallback if scraping fails).

Execute a series of predefined test queries:

Any flat 50% off deals today?

What are the top loyalty cashback offers on Nykaa?

Summarize the latest fashion discounts from Adidas

Summarize top deals (k=3)

List offers by brand: Nykaa

List offers by brand: Nike (demonstrates no offers found)

You can modify the if __name__ == "__main__": block in rag_query.py to add your own test queries.

Step 3: Run the Slackbot
To run the Slackbot, ensure your .env file is correctly configured with Slack tokens.

python slackbot.py

Upon running:

The bot will attempt to connect to Slack using Socket Mode.

It will perform an initial data ingestion check. If the database is empty, it will scrape and ingest data (or fall back to dummy data).

If successful, you will see logging messages indicating the bot is running.

If Slack tokens are missing or invalid, it will fall back to a simple CLI chatbot.

7. Slackbot Commands
Once the Slackbot is running and connected, you can interact with it in any channel it's invited to using the /promosensei slash command.

Query Offers:

/promosensei query Any deals on electronics?

Example Response: "Here are some relevant offers related to electronics..."

Summarize Top Deals:

/promosensei summary

Example Response: "Here's a summary of the top 5 deals: Nykaa Flat 50% Off on Makeup, Puma End of Season Sale..."

List Offers by Brand:

/promosensei brand Nykaa

Example Response: "Here are the promotional offers for the brand 'Nykaa': Offer 1: Title: Nykaa Flat 50% Off on Makeup..."

Refresh Data:

/promosensei refresh

This command will trigger a fresh scrape and re-ingestion of data into the vector database. This can take some time depending on the number of URLs configured.
Example Response: "Refreshing promotional offers data. This might take a moment..."

8. Logging
All modules (scraper.py, ingest_to_vector_db.py, rag_query.py, slackbot.py) are configured to use Python's logging module.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

Logs are printed to the console, providing real-time feedback on the scraping, ingestion, and query processes, as well as any warnings or errors encountered.

9. Future Enhancements
Dynamic Category Extraction: Improve the scraper to dynamically determine categories for Flipkart and Amazon products rather than using static defaults.

More Robust Expiry Date Parsing: Enhance _parse_expiry_date to handle a wider variety of date formats and relative date phrases.

Additional Website Support: Extend the scraper to include more e-commerce platforms.

Advanced Filtering: Implement more sophisticated filtering options for RAG queries (e.g., filter by price range, specific product types).

User Feedback Loop: Allow users to provide feedback on the relevance of LLM responses to improve future performance.

Scheduled Scraping: Implement a scheduler (e.g., using APScheduler) to automatically refresh data at regular intervals.

Deployment: Containerize the application (e.g., with Docker) for easier deployment to cloud platforms.
