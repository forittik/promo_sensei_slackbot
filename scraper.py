# scraper.py
import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime, timedelta
import logging
import json
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define configurable maximum page limit for Nykaa pagination
NYKAA_MAX_PAGES = 2 # Example: scrape first 5 pages, set to 0 for unlimited (use with caution)
# Define configurable maximum page limit for Flipkart pagination 
FLIPKART_MAX_PAGES = 2 # Example: scrape first 5 pages, set to 0 for unlimited (use with caution)
# Define configurable maximum page limit for Adidas pagination 
ADIDAS_MAX_PAGES = 2 # Example: scrape first 5 pages, set to 0 for unlimited (use with caution)

#For Amazon
MAX_OFFERS_PER_SITE=5 #this is for amzon maximum offers to be scrapped
SCRAPE_DELAY_MIN_SECONDS=1 
SCRAPE_DELAY_MAX_SECONDS=3

class WebScraper:
    def __init__(self, urls):
        self.urls = urls

    async def _scrape_page(self, page, url):
        offers_data = []
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            logging.info(f"Navigated to {url}. Current URL: {page.url}")

            await page.wait_for_timeout(3000)

            if "chrome-error" in page.url or "about:blank" in page.url:
                logging.warning(f"Navigation to {url} resulted in an unexpected page: {page.url}. Skipping scraping for this URL.")
                return []

            # --- Nykaa Scraping Logic ---
            if "nykaa.com/sp/offers-native/offers" in page.url:
                logging.info(f"Attempting to scrape Nykaa offers from {page.url}")

                banner_selector = 'div.outline-wrapper'
                try:
                    await page.wait_for_selector(banner_selector, state='visible', timeout=10000)
                    logging.info(f"Clicking banner: {banner_selector}")
                    await page.click(banner_selector)
                    await page.wait_for_load_state("networkidle")
                    logging.info(f"Navigated to new URL after banner click: {page.url}")

                    base_bestsellers_url = page.url
                    base_bestsellers_url = re.sub(r'([?&])page_no=\d+(&|$)', r'\1', base_bestsellers_url)
                    if not ('?' in base_bestsellers_url):
                        base_bestsellers_url += '?'
                    elif not base_bestsellers_url.endswith('&') and not base_bestsellers_url.endswith('?'):
                         base_bestsellers_url += '&'

                    total_pages = 1
                    try:
                        pagination_text_element = await page.query_selector("span.css-62qqre")
                        if pagination_text_element:
                            pagination_text = await pagination_text_element.text_content()
                            match = re.search(r'Page \d+ of (\d+)', pagination_text)
                            if match:
                                total_pages = int(match.group(1))
                                logging.info(f"Total pages identified on Nykaa bestsellers: {total_pages}")
                    except Exception as e:
                        logging.warning(f"Could not extract total pages for Nykaa pagination: {e}. Defaulting to 1 page.")

                    if NYKAA_MAX_PAGES > 0:
                        total_pages = min(total_pages, NYKAA_MAX_PAGES)
                        logging.info(f"Applying Nykaa max page limit. Will scrape up to {total_pages} pages.")

                    for page_no in range(1, total_pages + 1):
                        paginated_url = f"{base_bestsellers_url}page_no={page_no}"
                        logging.info(f"Scraping Nykaa bestsellers page: {paginated_url}")

                        await page.goto(paginated_url, wait_until="networkidle", timeout=60000)
                        await page.wait_for_timeout(2000)

                        html_content = await page.content()
                        from bs4 import BeautifulSoup
                        doc = BeautifulSoup(html_content, "html.parser")

                        product_containers = doc.find_all('div', class_='css-1rd7vky')

                        if not product_containers:
                            logging.warning(f"No product containers found on Nykaa bestsellers page {page_no}.")
                            nametags = doc.find_all('div', {'class': 'css-xrzmfa'})
                            if nametags:
                                logging.info(f"Found {len(nametags)} product name elements (fallback). Attempting to scrape details.")
                                originalprice_elements = doc.find_all('span', {'class':'css-17x46n5'})
                                offerprice_elements = doc.find_all('span', {'class':'css-111z9ua'})
                                discount_elements = doc.find_all('span', {'class':'css-r2b2eh'})
                                offer_elements = doc.find_all('p', {'class':'css-i6xqbh'})
                                reviews_elements = doc.find_all('span', {'class':'css-1j33oxj'})

                                max_len = max(len(nametags), len(originalprice_elements), len(offerprice_elements),
                                              len(discount_elements), len(offer_elements), len(reviews_elements))

                                def pad_list(lst, length):
                                    return lst + [None] * (length - len(lst))

                                padded_nametags = pad_list(nametags, max_len)
                                padded_originalprice = pad_list(originalprice_elements, max_len)
                                padded_offerprice = pad_list(offerprice_elements, max_len)
                                padded_discount = pad_list(discount_elements, max_len)
                                padded_offer = pad_list(offer_elements, max_len)
                                padded_reviews = pad_list(reviews_elements, max_len)

                                for i in range(max_len):
                                    try:
                                        name = padded_nametags[i].text.strip() if padded_nametags[i] else "N/A"
                                        op_text = "N/A"
                                        if padded_originalprice[i]:
                                            if padded_originalprice[i].name == 'span' and 'css-17x46n5' in padded_originalprice[i].get('class', []):
                                                op_text = padded_originalprice[i].text.strip()
                                            else:
                                                mrp_span = padded_originalprice[i].find('span', class_='css-17x46n5')
                                                if mrp_span:
                                                    op_text = mrp_span.text.strip()

                                            if op_text == 'MRP:':
                                                op_text = "N/A"

                                        offerp_text = padded_offerprice[i].text.strip() if padded_offerprice[i] else "N/A"
                                        dis_text = padded_discount[i].text.strip() if padded_discount[i] else "N/A"
                                        o_text = padded_offer[i].text.strip() if padded_offer[i] else "N/A"
                                        r_text = padded_reviews[i].text.strip() if padded_reviews[i] else "N/A"

                                        offers_data.append({
                                            "title": name,
                                            "description": f"Original Price: {op_text}, Offer Price: {offerp_text}, Discount: {dis_text}, Extra Offer: {o_text}",
                                            "expiry_date": None,
                                            "brand_name": "Nykaa",
                                            "offer_link": paginated_url,
                                            "category": "Beauty & Cosmetics",
                                            "campaign_info": o_text if o_text != "N/A" else None,
                                            "channels": "Website"
                                        })
                                    except Exception as e:
                                        logging.warning(f"Could not extract details for product {i} on Nykaa page {page_no} (fallback): {e}")
                            else:
                                logging.warning(f"No nametags found on Nykaa bestsellers page {page_no} (fallback failed).")
                        else:
                            for container in product_containers:
                                try:
                                    title = container.find('div', {'class': 'css-xrzmfa'}).text.strip() if container.find('div', {'class': 'css-xrzmfa'}) else "N/A"

                                    original_price_element = container.find('span', class_='css-17x46n5')
                                    original_price = original_price_element.text.strip() if original_price_element and original_price_element.text.strip() != 'MRP:' else "N/A"

                                    offer_price_element = container.find('span', class_='css-111z9ua')
                                    offer_price = offer_price_element.text.strip() if offer_price_element else "N/A"

                                    discount_element = container.find('span', class_='css-r2b2eh')
                                    discount = discount_element.text.strip() if discount_element else "N/A"

                                    free_gift_element = container.find('p', class_='css-i6xqbh')
                                    free_gift = free_gift_element.text.strip() if free_gift_element else "N/A"

                                    review_element = container.find('span', class_='css-1j33oxj')
                                    reviews = review_element.text.strip() if review_element else "N/A"

                                    product_link_element = container.find('a', href=True)
                                    product_link = "https://www.nykaa.com" + product_link_element['href'] if product_link_element and product_link_element['href'].startswith('/') else (product_link_element['href'] if product_link_element else paginated_url)

                                    offers_data.append({
                                        "title": title,
                                        "description": f"Original Price: {original_price}, Offer Price: {offer_price}, Discount: {discount}, Free Gift/Offer: {free_gift}, Reviews: {reviews}",
                                        "expiry_date": None,
                                        "brand_name": "Nykaa",
                                        "offer_link": product_link,
                                        "category": "Beauty & Cosmetics",
                                        "campaign_info": free_gift if free_gift != "N/A" else None,
                                        "channels": "Website"
                                    })
                                except Exception as e:
                                    logging.warning(f"Could not extract all details for a product from container on Nykaa page {page_no}: {e}")

                except Exception as e:
                    logging.error(f"Error clicking banner or processing new page on Nykaa: {e}")
                    content = await page.content()
                    offers_data.extend(self._generic_scrape(content, url, "Nykaa"))

            # --- Flipkart Scraping Logic ---
            elif "flipkart.com/offers-store" in page.url:
                logging.info(f"Attempting to scrape Flipkart offers from {page.url}")
                view_all_links = await page.query_selector_all("div.OtM6a6 a.QqFHMw.M5XAsp")
                original_flipkart_page = page 
                browser_context = await original_flipkart_page.context.browser.new_context()

                category_offers = []
                for link_element in view_all_links:
                    category_url = await link_element.get_attribute('href')
                    if category_url and not category_url.startswith('http'):
                        category_url = "https://www.flipkart.com" + category_url # Make absolute

                    if not category_url:
                        logging.warning("Could not extract href from a 'VIEW ALL' link.")
                        continue
                    
                    # Open a new page for each category link to avoid interference
                    category_page = await browser_context.new_page()
                    try:
                        logging.info(f"Navigating to Flipkart category page: {category_url}")
                        await category_page.goto(category_url, wait_until="networkidle", timeout=60000)
                        await category_page.wait_for_timeout(3000) # Give page time to load content

                        # The main product container is .mt4CeI, inside a .gwkl1B
                        product_listing_elements = await category_page.query_selector_all("div.gwkl1B div.mt4CeI")
                        
                        if not product_listing_elements:
                            logging.warning(f"No specific product listing elements found on Flipkart category page: {category_url}. Trying generic approach.")
                            content = await category_page.content()
                            category_offers.extend(self._generic_scrape(content, category_url, "Flipkart"))
                        else:
                            logging.info(f"Found {len(product_listing_elements)} product elements on {category_url}")
                            for product_element in product_listing_elements:
                                try:
                                    title_element = await product_element.query_selector("div.ZHvV68")
                                    title = await title_element.text_content() if title_element else "N/A"

                                    price_element = await product_element.query_selector("div.J5MN75")
                                    price = await price_element.text_content() if price_element else "N/A"
                                    
                                    description_element = await product_element.query_selector("div.H0KV9w")
                                    description = await description_element.text_content() if description_element else "N/A"

                                    product_link_element = await product_element.query_selector("a.x6h4az")
                                    product_link = await product_link_element.get_attribute('href') if product_link_element else category_url
                                    if product_link and not product_link.startswith('http'):
                                        product_link = "https://www.flipkart.com" + product_link

                                    discount = "N/A" # No explicit discount element in the provided HTML. Could infer from price text.

                                    # Get the category name from the original page
                                    # This is tricky because the element we need to query is on the 'original_flipkart_page'
                                    # but we need to find the specific h2 associated with the current 'view all' link.
                                    # This selector looks for an h2.T1JLc9 that is a sibling of the parent of the 'view all' link.
                                    parent_div_of_link = await original_flipkart_page.query_selector(f"a.QqFHMw.M5XAsp[href='{await link_element.get_attribute('href')}'] >> xpath=../..")
                                    category_name_element = await parent_div_of_link.query_selector("h2.T1JLc9")
                                    category_name_from_h2 = await category_name_element.text_content() if category_name_element else "Flipkart Category"


                                    category_offers.append({
                                        "title": title,
                                        "description": f"{description} | Price: {price}", # Combine price into description
                                        "expiry_date": None, # Flipkart product listings often don't have explicit expiry
                                        "brand_name": "Flipkart",
                                        "offer_link": product_link,
                                        "category": category_name_from_h2, # Use the extracted category name
                                        "campaign_info": f"Price: {price}", # Using price as campaign info if no discount
                                        "channels": "Website"
                                    })
                                except Exception as e:
                                    logging.warning(f"Could not extract details for a product on Flipkart category page {category_url}: {e}")
                    except Exception as e:
                        logging.error(f"Error navigating or scraping Flipkart category page {category_url}: {e}")
                    finally:
                        await category_page.close() 
                
                await browser_context.close()
                offers_data.extend(category_offers) 

            # --- NEW Flipkart Search Results Page Logic (for pagination and format) ---
            elif "flipkart.com/search" in page.url:
                logging.info(f"Attempting to scrape Flipkart search results from {url}")
                base_search_url = url
                base_search_url = re.sub(r'([?&])page=\d+(&|$)', r'\1', base_search_url)
                
                if '?' not in base_search_url:
                    base_search_url += '?'
                elif not base_search_url.endswith('&') and not base_search_url.endswith('?'):
                    base_search_url += '&'

                actual_total_pages_detected = 0 # To store the dynamically detected total pages
                try:
                    last_page_element = await page.query_selector("a.ge-49M:last-child")
                    if last_page_element:
                        last_page_text = await last_page_element.text_content()
                        if last_page_text.isdigit(): # Ensure it's a number before converting
                            actual_total_pages_detected = int(last_page_text)
                            logging.info(f"Dynamically detected total pages on Flipkart search results: {actual_total_pages_detected}")
                        else:
                            logging.warning(f"Extracted last page text '{last_page_text}' is not a digit. Will use configured max pages or default.")
                except Exception as e:
                    logging.warning(f"Could not extract total pages for Flipkart search pagination: {e}. Defaulting to 1 page.")

                total_pages_to_scrape = 1 # Default to at least 1 page
                
                if actual_total_pages_detected > 0:
                    # If actual pages were detected, use that value, but cap it by FLIPKART_MAX_PAGES if set
                    if FLIPKART_MAX_PAGES > 0:
                        total_pages_to_scrape = min(actual_total_pages_detected, FLIPKART_MAX_PAGES)
                    else: # FLIPKART_MAX_PAGES is 0, meaning unlimited
                        total_pages_to_scrape = actual_total_pages_detected
                else:
                    # If no actual pages were detected, default to FLIPKART_MAX_PAGES
                    total_pages_to_scrape = FLIPKART_MAX_PAGES if FLIPKART_MAX_PAGES > 0 else 1

                logging.info(f"Applying Flipkart max page limit. Will scrape up to {total_pages_to_scrape} pages.")

                for page_no in range(1, total_pages_to_scrape + 1):
                    paginated_url = f"{base_search_url}page={page_no}"
                    logging.info(f"Scraping Flipkart search results page: {paginated_url}")
                    await page.goto(paginated_url, wait_until="networkidle", timeout=60000)
                    await page.wait_for_timeout(2000)
                    html_content = await page.content()
                    from bs4 import BeautifulSoup
                    doc = BeautifulSoup(html_content, "html.parser")

                    product_cards = doc.find_all('div', class_='slAVV4') 

                    if not product_cards:
                        logging.warning(f"No specific product cards ('slAVV4') found on Flipkart search results page {page_no}. Skipping this page for specific offer extraction.")
                        continue 
                    else:
                        logging.info(f"Found {len(product_cards)} product cards on {paginated_url}")
                        for card in product_cards:
                            try:
                                title_element = card.find('a', class_='wjcEIp')
                                title = title_element.get('title', '').strip() if title_element else "N/A"
                                if title == "N/A" and title_element:
                                    title = title_element.text.strip()

                                product_link_element = card.find('a', class_='VJA3rP')
                                if not product_link_element: 
                                    product_link_element = card.find('a', class_='wjcEIp')

                                product_link = "https://www.flipkart.com" + product_link_element['href'] if product_link_element and product_link_element['href'].startswith('/') else (product_link_element['href'] if product_link_element else "N/A")

                                offer_price_element = card.find('div', class_='Nx9bqj')
                                offer_price = offer_price_element.text.strip() if offer_price_element else "N/A"

                                original_price_element = card.find('div', class_='yRaY8j')
                                original_price = original_price_element.text.strip() if original_price_element else "N/A"

                                discount_element = card.find('div', class_='UkUFwK')
                                discount = discount_element.text.strip() if discount_element else "N/A"

                                description_parts = []
                                pack_info_element = card.find('div', class_='NqpwHC')
                                if pack_info_element and pack_info_element.text.strip() != "":
                                    description_parts.append(pack_info_element.text.strip())
                                
                                description_parts.append(f"Original Price: {original_price}, Offer Price: {offer_price}, Discount: {discount}")

                                hot_deal_element = card.find('div', class_='M4DNwV div.yiggsN.O5Fpg8')
                                if hot_deal_element and hot_deal_element.text.strip() != "":
                                    description_parts.append(hot_deal_element.text.strip())

                                description = " | ".join(description_parts) if description_parts else "N/A"

                                rating_element = card.find('div', class_='XQDdHH')
                                rating = rating_element.text.strip() if rating_element else "N/A"

                                num_reviews_element = card.find('span', class_='Wphh3N')
                                num_reviews = num_reviews_element.text.strip() if num_reviews_element else "N/A"

                                offers_data.append({
                                    "title": title,
                                    "description": description,
                                    "expiry_date": None, # Expiry date is usually not on search result cards
                                    "brand_name": "Flipkart", 
                                    "offer_link": product_link,
                                    "category": "Beauty & Cosmetics", 
                                    "campaign_info": discount if discount != "N/A" else None,
                                    "channels": "Website",
                                    "rating": rating, 
                                    "num_reviews": num_reviews 
                                })
                            except Exception as e:
                                logging.warning(f"Could not extract details for a product card on Flipkart search results page {page_no}: {e}")


            # elif "adidas.co.in/offers" in page.url:
            elif "adidas.co.in/offers" in page.url:
                logging.info(f"Attempting to scrape Adidas offers from {page.url}")

                product_card_locators = page.locator('article[data-testid="plp-product-card"]')
                offers_elements = await product_card_locators.all()

                if not offers_elements:
                    logging.warning(f"No specific product card elements found on Adidas for {page.url}. This might indicate a selector issue or no products on page.")
                
                for element_handle in offers_elements:
                    try:
                        title_locator = element_handle.locator('p[data-testid="product-card-title"]').first
                        title = await title_locator.text_content(timeout=2000)
                        if title:
                            title = title.strip()
                        else:
                            logging.debug(f"Could not find title for an Adidas product card. Skipping this card.")
                            continue

                        description_parts = []

                        subtitle_locator = element_handle.locator('p[data-testid="product-card-subtitle"]').first
                        subtitle = await subtitle_locator.text_content(timeout=1000) or ""
                        if subtitle.strip():
                            description_parts.append(subtitle.strip())

                        colours_locator = element_handle.locator('p[data-testid="product-card-colours"]').first
                        colours = await colours_locator.text_content(timeout=1000) or ""
                        if colours.strip():
                            description_parts.append(colours.strip())
                        
                        current_price_locator = element_handle.locator('div[data-testid="main-price"] span:not([class*="_visuallyHidden_"])').first
                        current_price = await current_price_locator.text_content(timeout=1000) or ""
                        if current_price.strip():
                            description_parts.append(f"Current Price: {current_price.strip()}")

                        original_price = ""
                        try:
                            original_price_locator = element_handle.locator('div[data-testid="price-component"] span.gl-price__value--original').first
                            if await original_price_locator.is_visible(timeout=2000): # Increased timeout here
                                original_price = await original_price_locator.text_content(timeout=1000) or ""
                            if original_price.strip():
                                description_parts.append(f"Original Price: {original_price.strip()}")
                        except Exception as price_e:
                            logging.debug(f"Original price not found or error for product '{title}': {price_e}")

                        description = " | ".join(description_parts) if description_parts else "Product details"

                        campaign_info_locator = element_handle.locator('p[data-testid="product-card-badge"]').first
                        campaign_info = await campaign_info_locator.text_content(timeout=1000) or None
                        if campaign_info:
                            campaign_info = campaign_info.strip()

                        expiry_date = None # Adidas product cards usually don't have explicit expiry dates
                        brand_name = "Adidas"

                        offer_link_locator = element_handle.locator('a[data-testid="product-card-description-link"]').first
                        offer_link = await offer_link_locator.get_attribute("href", timeout=2000) or page.url
                        if offer_link and not offer_link.startswith("http"):
                            base_url = "https://www.adidas.co.in" 
                            offer_link = f"{base_url}{offer_link}"

                        category = "Apparel & Footwear" 
                        channels = "Website"

                        offers_data.append({
                            "title": title,
                            "description": description,
                            "expiry_date": expiry_date,
                            "brand_name": brand_name,
                            "offer_link": offer_link,
                            "category": category,
                            "campaign_info": campaign_info,
                            "channels": channels
                        })
                    except Exception as e:
                        logging.warning(f"Could not extract all details for an Adidas product card: {e}")

                if not offers_data: 
                    logging.warning(f"No specific product offers found on Adidas for {page.url}. Attempting generic scrape as fallback.")
                    content = await page.content()
                    generic_offers = self._generic_scrape(content, url, "Adidas")
                    offers_data.extend(generic_offers)
                else:
                    logging.info(f"Successfully scraped {len(offers_data)} specific Adidas offers.")

            # --- Puma Scraping Logic ---
            elif "in.puma.com/in/en/puma-sale-collection" in page.url:
                logging.info(f"Attempting to scrape Puma offers from {page.url}")
                offers_elements = await page.query_selector_all(".product-tile, .category-page-product-tile")
                
                if not offers_elements:
                    logging.warning(f"No specific offer elements found on Puma for {page.url}. Trying generic approach.")

                for element in offers_elements:
                    try:
                        title = await element.query_selector_eval(".product-tile__name, .product-name", "el => el.textContent.trim()")
                        description = await element.query_selector_eval(".product-tile__price-discount, .product-price, .product-tile__subtitle", "el => el.textContent.trim()")
                        expiry_date = None
                        brand_name = "Puma"
                        offer_link = await element.query_selector_eval("a.product-tile__link, a.link", "el => el.href")
                        category = "Apparel & Footwear"
                        campaign_info = None
                        channels = None

                        offers_data.append({
                            "title": title,
                            "description": description,
                            "expiry_date": expiry_date,
                            "brand_name": brand_name,
                            "offer_link": offer_link,
                            "category": category,
                            "campaign_info": campaign_info,
                            "channels": channels
                        })
                    except Exception as e:
                        logging.warning(f"Could not extract all details for an offer on Puma: {e}")
                
                if not offers_data:
                    content = await page.content()
                    offers_data.extend(self._generic_scrape(content, url, "Puma"))


            # --- Amazon Deals Page Scraping Logic (Visits individual product pages) ---
            elif "amazon.in/deals" in page.url:
                logging.info(f"Attempting to collect individual deal links from Amazon deals page: {page.url}")
                
                deal_links = []
                # Selectors for links within deal cards on the Amazon deals page
                link_elements = await page.locator("div[data-deal-id] a.a-link-normal, div.deal-card a.a-link-normal, div.octopus-pc-item a.a-link-normal").all()
                for link_el in link_elements:
                    href = await link_el.get_attribute('href')
                    if href:
                        full_url = "https://www.amazon.in" + href if href.startswith('/') else href
                        deal_links.append(full_url)
                
                logging.info(f"Found {len(deal_links)} potential deal links on Amazon deals page.")

                browser_context = await page.context.browser.new_context()
                offers_count = 0
                for deal_link in deal_links:
                    if offers_count >= MAX_OFFERS_PER_SITE and MAX_OFFERS_PER_SITE > 0:
                        logging.info(f"Reached MAX_OFFERS_PER_SITE ({MAX_OFFERS_PER_SITE}) for Amazon. Stopping scraping.")
                        break

                    deal_page = await browser_context.new_page()
                    try:
                        logging.info(f"Scraping individual Amazon deal: {deal_link}")
                        await deal_page.goto(deal_link, wait_until="domcontentloaded", timeout=60000)
                        await asyncio.sleep(random.uniform(SCRAPE_DELAY_MIN_SECONDS / 2, SCRAPE_DELAY_MAX_SECONDS / 2)) # Shorter delay for individual items

                        await deal_page.wait_for_selector("#productTitle, #a-page h1 span#productTitle", timeout=30000)

                        title_element_handle = await deal_page.locator("#productTitle, #a-page h1 span#productTitle").first.element_handle()
                        title = (await title_element_handle.text_content()).strip() if title_element_handle else "N/A"

                        price_element_handle = await deal_page.locator(".priceToPay span.a-price-whole, #priceblock_ourprice, #apex_desktop span.a-price-whole, .a-offscreen").first.element_handle()
                        price = (await price_element_handle.text_content()).strip() if price_element_handle else "N/A"

                        description_element_handle = await deal_page.locator("#productDescription, #feature-bullets").first.element_handle()
                        description = (await description_element_handle.text_content()).strip() if description_element_handle else "N/A"
                        
                        brand_element_handle = await deal_page.locator("#bylineInfo, #brand").first.element_handle()
                        brand_name = (await brand_element_handle.text_content()).strip() if brand_element_handle else "Amazon"
                
                        if "Visit the" in brand_name and "Store" in brand_name:
                            brand_name = brand_name.replace("Visit the", "").replace("Store", "").strip()


                        offers_data.append({
                            "title": title if title else "N/A",
                            "description": f"{description} | Price: {price}" if description != "N/A" or price != "N/A" else "N/A",
                            "expiry_date": None, # Amazon product pages usually don't have explicit deal expiry dates
                            "brand_name": brand_name,
                            "offer_link": deal_link,
                            "category": "E-commerce", 
                            "campaign_info": f"Deal Price: {price}" if price != "N/A" else None,
                            "channels": "Website"
                        })
                        offers_count += 1
                    except Exception as e:
                        logging.warning(f"Could not extract details for Amazon deal page {deal_link}: {e}")
                    finally:
                        await deal_page.close() 
                await browser_context.close()


        
            else:
                logging.info(f"Attempting generic scrape for {page.url}")
                content = await page.content()
                offers_data.extend(self._generic_scrape(content, url, "Unknown"))

        except Exception as e: 
            logging.error(f"Error scraping {url}: {e}")
        return offers_data 
    def _generic_scrape(self, content, url, brand_name="Unknown Brand"):
        """
        A very basic generic scrape that looks for common offer-like phrases.
        This is a fallback and will likely be less accurate than site-specific logic.
        It tries to avoid picking up generic class names as titles/descriptions.
        """
        generic_offers = []
        potential_matches = re.finditer(r"(?:[0-9]{1,3}% off|flat \d+%|cashback|sale|discount|deal|promo)\b.*?(?:\.|\n|$)", content, re.IGNORECASE | re.DOTALL)
        
        for match in potential_matches:
            text = match.group(0).strip()
            if len(text) < 15 or re.match(r"^[a-z0-9_-]+$", text): # Basic filter for class names
                continue

            title = text.split("\n")[0].strip() if text else "Generic Offer"
            description = text
            expiry_date = self._parse_expiry_date(text) # Try to parse date from generic text
            
            if re.match(r"sale-price|sale-offers", title, re.IGNORECASE):
                title = "Generic Sale/Offer"
            if re.match(r"sale-price|sale-offers", description, re.IGNORECASE):
                description = "Generic Sale/Offer details available on the page."

            generic_offers.append({
                "title": title,
                "description": description,
                "expiry_date": expiry_date,
                "brand_name": brand_name,
                "offer_link": url,
                "category": "Generic",
                "campaign_info": "Inferred from content",
                "channels": "Website"
            })
        return generic_offers


    def _parse_expiry_date(self, date_string):
        """
        Attempts to parse various date formats. This will require robustness.
        Example: "Ends May 23, 2025", "Valid till 23/05/2025", "Expires 2025-05-23"
        """
        if not date_string:
            return None
        formats = [
            "%B %d, %Y",    # May 23, 2025
            "%d/%m/%Y",     # 23/05/2025
            "%Y-%m-%d",     # 2025-05-23
            "%d %B %Y",     # 23 May 2025
            "%b %d, %Y",    # May 23, 2025 (abbreviated month)
            "%d %b %Y"      # 23 May 2025 (abbreviated month)
        ]
        for fmt in formats:
            try:
                match = re.search(r'(?:ends|expires|valid till|till)\s*(\w+\s+\d{1,2},\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}\s+\w+\s+\d{4})', date_string, re.IGNORECASE)
                if match:
                    date_part = match.group(1).strip()
                    return datetime.strptime(date_part, fmt).isoformat()
            except ValueError:
                continue

        current_date = datetime.now()
        if "today" in date_string.lower():
            return (current_date + timedelta(days=0)).isoformat()
        if "tomorrow" in date_string.lower():
            return (current_date + timedelta(days=1)).isoformat()
        if "next week" in date_string.lower():
            return (current_date + timedelta(weeks=1)).isoformat()
        if "next month" in date_string.lower():
            return (current_date + timedelta(days=30)).isoformat() 

        return None

    def _extract_brand_from_url(self, url):
        """Extracts brand name from URL for generic scraping."""
        match = re.search(r"(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+)\.com", url)
        if match:
            return match.group(1).capitalize()
        return "Unknown Brand"

    async def scrape_all(self):
        all_offers = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False) 
            page = await browser.new_page()
            for url in self.urls:
                logging.info(f"Starting scrape for {url}")
                offers = await self._scrape_page(page, url)
                all_offers.extend(offers)
                logging.info(f"Finished scraping {url}. Found {len(offers)} offers.")
            await browser.close()
        return all_offers

if __name__ == "__main__":
    from config import SCRAPE_URLS
    scraper = WebScraper(SCRAPE_URLS)
    scraped_data = asyncio.run(scraper.scrape_all())

    # Save scraped data to a JSON file
    output_filename = "scraped_offers.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=4)
    print(f"\nScraped data saved to {output_filename}")

    for offer in scraped_data:
        print(offer)
    print(f"\nTotal offers scraped: {len(scraped_data)}")