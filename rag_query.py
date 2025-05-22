# rag_query.py
from openai import OpenAI
from ingest_to_vector_db import VectorDBManager
from config import LLM_MODEL, OPENAI_API_KEY
import logging
from datetime import datetime
import re 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RAGQueryProcessor:
    def __init__(self):
        self.db_manager = VectorDBManager()
        self.llm_client = OpenAI(api_key=OPENAI_API_KEY)
        self.llm_model = LLM_MODEL

    def _clean_flipkart_url(self, url):
        """
        Cleans up Flipkart URLs by removing common tracking parameters.
        Preserves essential query parameters like 'sid' and 'collection-tab-name'.
        """
        if "flipkart.com" in url:
            # Regex to remove specific tracking parameters: param, hpid, ctx
            # It looks for these parameters and their values, followed by '&' or end of string
            cleaned_url = re.sub(r'(&param=[^&]*|&hpid=[^&]*|&ctx=[^&]*)', '', url)
            
            # Clean up any trailing '&' or '?' that might be left after removals
            if cleaned_url.endswith('&'):
                cleaned_url = cleaned_url.rstrip('&')
            if cleaned_url.endswith('?'):
                cleaned_url = cleaned_url.rstrip('?')
            
            return cleaned_url
        return url

    def _format_offers_for_llm(self, offers):
        if not offers:
            return "No relevant offers found."

        formatted_string = "Here are the relevant promotional offers:\n\n"
        for i, offer in enumerate(offers):
            title = offer.get('title', 'N/A')
            description = offer.get('description', 'N/A')
            brand = offer.get('brand_name', 'N/A')
            expiry = offer.get('expiry_date', 'N/A')
            link = offer.get('offer_link', 'N/A')

            # Clean Flipkart URLs before formatting for LLM
            if brand and 'flipkart' in brand.lower() and link and link != 'N/A':
                link = self._clean_flipkart_url(link)

            formatted_string += f"Offer {i+1}:\n"
            formatted_string += f"  Title: {title}\n"
            formatted_string += f"  Description: {description}\n"
            formatted_string += f"  Brand: {brand}\n"
            formatted_string += f"  Expiry Date: {expiry}\n"
            
            if link and link != 'N/A':
                formatted_string += f"  Link: [View Offer]({link})\n\n"
            else:
                formatted_string += f"  Link: N/A\n\n"
        return formatted_string

    def query_llm(self, user_query):
        # 1. Retrieve relevant offers from the vector database
        retrieved_offers = self.db_manager.search_offers(user_query, k=20) # Retrieve top 5 relevant offers
        logging.info(f"Retrieved {len(retrieved_offers)} offers for query: '{user_query}'")

        # 2. Format the retrieved offers as context for the LLM
        context = self._format_offers_for_llm(retrieved_offers)

        if "No relevant offers found" in context:
            prompt = (
                f"The user asked: '{user_query}'. "
                "I could not find any relevant offers in the database. "
                "Please respond politely that no relevant offers were found for their query."
            )
        else:
            prompt = (
                "You are Promo Sensei, a helpful assistant that provides information about promotional offers. "
                "Based on the following retrieved promotional offers, answer the user's query concisely and clearly. "
                "If an offer is expired, mention it. Prioritize active offers. "
                "Make sure to include the offer title, description, brand, and expiry date if available. "
                "**Crucially, format any links as concise Markdown links like [View Offer](URL) and do NOT expand the full URL text.** "
                "If the query is for a summary, provide a concise summary of the offers. "
                "If the query is for a specific brand, list offers from that brand. "
                "Contextual Offers:\n"
                f"{context}\n\n"
                f"User Query: {user_query}\n"
                "Your Answer:"
            )

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for promotional offers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error querying LLM: {e}")
            return "I apologize, but I encountered an error while processing your request. Please try again later."

    def summarize_top_deals(self, k=5):
        logging.info("Summarizing top deals.")
        all_offers = self.db_manager.metadata_store # Get all stored offers
        
        offers_to_summarize = all_offers[-k:] if len(all_offers) > k else all_offers

        if not offers_to_summarize:
            return "No deals are currently available to summarize."

        context = self._format_offers_for_llm(offers_to_summarize)
        prompt = (
            "You are Promo Sensei, a helpful assistant. "
            "Based on the following promotional offers, provide a concise summary of the top deals. "
            "Highlight key discounts, brands, and categories. If an offer is expired, mention it. "
            "Prioritize active offers. **Format any links as concise Markdown links like [View Offer](URL) and do NOT expand the full URL text.**\n\n"
            f"Contextual Offers:\n{context}\n\n"
            "Your Summary:"
        )
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for promotional offers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error summarizing deals with LLM: {e}")
            return "I apologize, but I encountered an error while summarizing deals. Please try again later."

    def list_offers_by_brand(self, brand_name):
        logging.info(f"Listing offers for brand: {brand_name}")
        
        if not self.db_manager.metadata_store:
            return f"No offers available in the database to search for {brand_name}."

        brand_offers = [
            offer for offer in self.db_manager.metadata_store
            if offer.get('brand_name', '').lower() == brand_name.lower()
        ]

        if not brand_offers:
            return f"I couldn't find any offers for {brand_name} at the moment."

        formatted_offers = self._format_offers_for_llm(brand_offers)
        prompt = (
            f"You are Promo Sensei, a helpful assistant. "
            f"Here are the promotional offers for the brand '{brand_name}':\n\n"
            f"{formatted_offers}\n\n"
            f"Please present these offers clearly and concisely to the user, focusing on key details like title, description, and expiry. "
            f"If any are expired, mention it. **Format any links as concise Markdown links like [View Offer](URL) and do NOT expand the full URL text.** "
            "Your Answer:"
        )
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for promotional offers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error listing offers by brand with LLM: {e}")
            return "I apologize, but I encountered an error while retrieving offers for the specified brand. Please try again later."


if __name__ == "__main__":
    # Ensure data is ingested before running RAG queries
    # You might run ingest_to_vector_db.py separately or call its main function
    from ingest_to_vector_db import VectorDBManager
    from scraper import WebScraper
    from config import SCRAPE_URLS
    import asyncio

    print("--- Ensuring data is ingested for RAG queries ---")
    db_manager_init = VectorDBManager()
    if not db_manager_init.metadata_store:
        print("Database is empty, attempting to scrape and ingest data...")
        try:
            scraper = WebScraper(SCRAPE_URLS)
            scraped_offers = asyncio.run(scraper.scrape_all())
            if scraped_offers:
                db_manager_init.ingest_data(scraped_offers)
                print(f"Ingested {len(scraped_offers)} offers.")
            else:
                print("No offers scraped. RAG queries might not be effective.")

        except Exception as e:
            print(f"Error during initial data ingestion for RAG testing: {e}")
            print("Please ensure your OpenAI API key is set and you have connectivity.")
    else:
        print("Database already has data. Proceeding with RAG queries.")

    processor = RAGQueryProcessor()

    print("\n--- Testing RAG Query: 'Any flat 50% off deals today?' ---")
    response = processor.query_llm("Any flat 50% off deals today?")
    print(response)
