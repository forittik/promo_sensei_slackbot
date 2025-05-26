# config.py
import os

from dotenv import load_dotenv 

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"DEBUG: OPENAI_API_KEY loaded: '{OPENAI_API_KEY}'")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

FAISS_DB_PATH = "data/faiss_index" 


SCRAPE_URLS = [
    # "https://www.nykaa.com/sp/offers-native/offers",
     "https://www.flipkart.com/offers-store",
    # "https://www.flipkart.com/search?q=beauty+and+cosmetics&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&p%5B%5D=facets.discount_range_v1%255B%255D%3D70%2525%2Bor%2Bmore&p%5B%5D=facets.discount_range_v1%255B%255D%3D60%2525%2Bor%2Bmore&p%5B%5D=facets.discount_range_v1%255B%255D%3D40%2525%2Bor%2Bmore&p%5B%5D=facets.discount_range_v1%255B%255D%3D50%2525%2Bor%2Bmore&p%5B%5D=facets.discount_range_v1%255B%255D%3D30%2525%2Bor%2Bmore&page=1",
    # "https://www.adidas.co.in/offers",
    #"https://www.amazon.in/deals?ref_=nav_cs_gb",
]

#For Flipkart, you can replace "beauty+and+cosmetics" with any product name, and it will work as is. Eg- Mobile

OFFER_DETAILS_SCHEMA = {
    "title": None,
    "description": None,
    "expiry_date": None,
    "brand_name": None,
    "offer_link": None,
    "category": None, # Added for vector DB metadata
    "campaign_info": None, # Additional output
    "channels": None # Additional output
}

# LLM Model
LLM_MODEL = "gpt-4o-mini"

# Embedding Model
EMBEDDING_MODEL = "text-embedding-3-small"
