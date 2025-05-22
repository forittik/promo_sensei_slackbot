# ingest_to_vector_db.py
import openai
from openai import OpenAI
import faiss
import numpy as np
import pickle
import os
import logging
import json 

from config import OPENAI_API_KEY, FAISS_DB_PATH, EMBEDDING_MODEL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VectorDBManager:
    def __init__(self, db_path=FAISS_DB_PATH, embedding_model=EMBEDDING_MODEL):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.embedding_model = embedding_model
        self.db_path = db_path
        self.index = None
        self.metadata_store = [] 
        self._load_or_initialize_db()

    def _load_or_initialize_db(self):
        index_file = self.db_path + ".bin"
        metadata_file = self.db_path + "_metadata.pkl"

        if os.path.exists(index_file) and os.path.exists(metadata_file):
            logging.info(f"Loading existing FAISS index from {index_file}")
            self.index = faiss.read_index(index_file)
            with open(metadata_file, "rb") as f:
                self.metadata_store = pickle.load(f)
            logging.info(f"Loaded {len(self.metadata_store)} existing records.")
        else:
            logging.info("Initializing new FAISS index.")
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                logging.info(f"Created directory: {db_dir}")
            self.index = None 
            self.metadata_store = []

    def _get_embedding(self, text):
        try:
            text = text.replace("\n", " ")
            response = self.client.embeddings.create(input=[text], model=self.embedding_model)
            return response.data[0].embedding
        except openai.OpenAIError as e:
            logging.error(f"Error getting embedding: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred while getting embedding: {e}")
            return None

    def ingest_data(self, offers_data):
        if not offers_data:
            logging.warning("No offers data provided for ingestion.")
            return

        new_embeddings = []
        new_metadata = []

        for i, offer in enumerate(offers_data):
            text_to_embed = (
                f"Title: {offer.get('title', '')}. "
                f"Description: {offer.get('description', '')}. "
                f"Brand: {offer.get('brand_name', '')}. "
                f"Category: {offer.get('category', '')}. " 
                f"Expiry: {offer.get('expiry_date', 'N/A')}."
            )
            embedding = self._get_embedding(text_to_embed)
            if embedding:
                new_embeddings.append(embedding)
                new_metadata.append(offer) 

        if not new_embeddings:
            logging.info("No valid embeddings generated for ingestion.")
            return

        embeddings_np = np.array(new_embeddings).astype('float32')

        if self.index is None:
            dimension = embeddings_np.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            logging.info(f"FAISS index initialized with dimension: {dimension}")

        logging.info(f"Adding {len(embeddings_np)} new embeddings to FAISS index.")
        self.index.add(embeddings_np)
        self.metadata_store.extend(new_metadata)

        self._save_db()
        logging.info("Data ingestion complete and FAISS index saved.")

    def _save_db(self):
        logging.info(f"Saving FAISS index to {self.db_path}.bin")
        faiss.write_index(self.index, self.db_path + ".bin")
        with open(self.db_path + "_metadata.pkl", "wb") as f:
            pickle.dump(self.metadata_store, f)
        logging.info("FAISS index and metadata saved successfully.")

    def search_offers(self, query_text, k=5):
        if self.index is None or not self.metadata_store:
            logging.warning("FAISS index is not initialized or empty. Cannot perform search.")
            return []

        query_embedding = self._get_embedding(query_text)
        if query_embedding is None:
            return []

        query_embedding_np = np.array([query_embedding]).astype('float32')

        D, I = self.index.search(query_embedding_np, k) # D are distances, I are indices
        logging.info(f"Found {len(I[0])} results for query.")

        results = []
        for idx in I[0]:
            if idx < len(self.metadata_store): 
                results.append(self.metadata_store[idx])
        return results

if __name__ == "__main__":
    from scraper import WebScraper
    from config import SCRAPE_URLS

    # --- Load from scraped_offers.json first if available ---
    json_filename = "scraped_offers.json"
    scraped_offers = []
    if os.path.exists(json_filename):
        logging.info(f"Loading offers from {json_filename}...")
        try:
            with open(json_filename, "r", encoding="utf-8") as f:
                scraped_offers = json.load(f)
            logging.info(f"Loaded {len(scraped_offers)} offers from {json_filename}.")
        except Exception as e:
            logging.error(f"Error loading {json_filename}: {e}. Attempting live scrape.")
            scraped_offers = [] # Reset to empty if loading fails
    
    if not scraped_offers:
        logging.info("No offers loaded from JSON or JSON load failed. Attempting live scrape.")
        try:
            scraper = WebScraper(SCRAPE_URLS)
            scraped_offers = asyncio.run(scraper.scrape_all())
            if not scraped_offers:
                logging.warning("No offers scraped from live sites. Using dummy data for demonstration.")
                # scraped_offers = [
                #     {"title": "Nykaa Flat 50% Off on Makeup", "description": "Get flat 50% off on selected makeup brands on Nykaa.", "expiry_date": "2025-06-30", "brand_name": "Nykaa", "offer_link": "https://www.nykaa.com/offers", "category": "Beauty & Cosmetics", "campaign_info": None, "channels": None},
                #     {"title": "Puma End of Season Sale", "description": "Up to 40% off on Puma footwear and apparel.", "expiry_date": "2025-05-28", "brand_name": "Puma", "offer_link": "https://in.puma.com/in/en/puma-sale-collection", "category": "Apparel & Footwear", "campaign_info": None, "channels": None},
                #     {"title": "Flipkart Big Billion Days Cashback", "description": "Earn 10% cashback on all electronics during Flipkart's Big Billion Days.", "expiry_date": "2025-06-15", "brand_name": "Flipkart", "offer_link": "https://www.flipkart.com/offers-store", "category": "E-commerce", "campaign_info": None, "channels": None},
                #     {"title": "Adidas Summer Collection Discount", "description": "New summer collection with 20% off for first-time buyers.", "expiry_date": "2025-07-31", "brand_name": "Adidas", "offer_link": "https://www.adidas.co.in/offers", "category": "Apparel & Footwear", "campaign_info": None, "channels": None},
                #     {"title": "Amazon Great Indian Festival Deals", "description": "Daily deals on a wide range of products.", "expiry_date": None, "brand_name": "Amazon", "offer_link": "https://www.amazon.in/deals", "category": "E-commerce", "campaign_info": None, "channels": None},
                # ]
        except Exception as e:
            logging.error(f"Error during scraping simulation: {e}. Using dummy data as fallback.")
            # scraped_offers = [
            #     {"title": "Nykaa Flat 50% Off on Makeup", "description": "Get flat 50% off on selected makeup brands on Nykaa.", "expiry_date": "2025-06-30", "brand_name": "Nykaa", "offer_link": "https://www.nykaa.com/offers", "category": "Beauty & Cosmetics", "campaign_info": None, "channels": None},
            #     {"title": "Puma End of Season Sale", "description": "Up to 40% off on Puma footwear and apparel.", "expiry_date": "2025-05-28", "brand_name": "Puma", "offer_link": "https://in.puma.com/in/en/puma-sale-collection", "category": "Apparel & Footwear", "campaign_info": None, "channels": None},
            #     {"title": "Flipkart Big Billion Days Cashback", "description": "Earn 10% cashback on all electronics during Flipkart's Big Billion Days.", "expiry_date": "2025-06-15", "brand_name": "Flipkart", "offer_link": "https://www.flipkart.com/offers-store", "category": "E-commerce", "campaign_info": None, "channels": None},
            #     {"title": "Adidas Summer Collection Discount", "description": "New summer collection with 20% off for first-time buyers.", "expiry_date": "2025-07-31", "brand_name": "Adidas", "offer_link": "https://www.adidas.co.in/offers", "category": "Apparel & Footwear", "campaign_info": None, "channels": None},
            #     {"title": "Amazon Great Indian Festival Deals", "description": "Daily deals on a wide range of products.", "expiry_date": None, "brand_name": "Amazon", "offer_link": "https://www.amazon.in/deals", "category": "E-commerce", "campaign_info": None, "channels": None},
            # ]


    db_manager = VectorDBManager()
    # Only ingest if there's data and the DB is empty or needs refresh
    if scraped_offers and not db_manager.metadata_store:
        db_manager.ingest_data(scraped_offers)
    elif scraped_offers and db_manager.metadata_store:
        logging.info("Database already contains data. To refresh, delete faiss_index.bin and faiss_index_metadata.pkl and rerun.")


   