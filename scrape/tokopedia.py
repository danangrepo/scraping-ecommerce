import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import os
load_dotenv()

# create class tokopedia
class Tokopedia:
    def __init__(self, query = "", page="1", filter="best-match"):
        self.url = os.getenv("TOKPED_URL")
        self.endpoint_product = os.getenv("TOKPED_ENDPOINT_PRODUCT")
        self.endpoint_promo = os.getenv("TOKPED_ENDPOINT_PROMO")
        self.query = query
        self.page = page
        self.data = []
        self.filter_data = [
            {
                "name": "Paling Sesuai",
                "value": "best-match",
                "ob": 23
            },
            {
                "name": "Terbaru",
                "value": "newest",
                "ob": 9
            },
            {
                "name": "Harga Terendah",
                "value": "price-asc",
                "ob": 3
            },
            {
                "name": "Harga Tertinggi",
                "value": "price-desc",
                "ob": 4
            },
            {
                "name": "Ulasan",
                "value": "rating",
                "ob": 5
            }
        ]

        match filter:
            case "best-match":
                self.filter = self.filter_data[0]
            case "newest":
                self.filter = self.filter_data[1]
            case "price-asc":
                self.filter = self.filter_data[2]
            case "price-desc":
                self.filter = self.filter_data[3]
            case "rating":
                self.filter = self.filter_data[4]
            case _:
                self.filter = self.filter_data[0]

        self.url = f"https://www.tokopedia.com/search?ob={self.filter['ob']}&page={self.page}&q={self.query}&st=product&navsource="

    def sync_scrape_data(self):
        """Menjalankan Playwright dalam event loop tersendiri."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.playwright_scrape())
    
    async def playwright_scrape(self):
        """Fungsi async untuk scraping menggunakan Playwright"""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            tabPage = await browser.new_page()

            # add promo produk
            async def handle_response(response):
                if self.endpoint_product in response.url:
                    json_data = await response.json()
                    self.data.append(json_data)

            # Pasang listener sebelum membuka halaman
            tabPage.on("response", lambda response: asyncio.create_task(handle_response(response)))
            await tabPage.goto(self.url)
            
            await tabPage.click("//button[contains(@data-unify, 'Select')]", timeout=500)
            await asyncio.sleep(3)
            best_match_option = await tabPage.query_selector(f'button[data-item-text="Paling Sesuai"]')
            await best_match_option.click()
            await asyncio.sleep(1)
                
                
            await browser.close()
            return self.data
        
    def get_product(self, data=[]):
        result = []
        response = data[0][0]["data"]["searchProductV5"]["data"]["products"]
        for i, product in enumerate(response):
            result.append({
                "id": product["id"],
                "url": product["url"],
                "media_url": [
                    product["mediaURL"]["image"],
                    product["mediaURL"]["image300"],
                    product["mediaURL"]["videoCustom"]
                ],
                "name": product["name"],
                "price": [
                    {
                        "discount_percentage": product["price"]["discountPercentage"],
                        "number": product["price"]["number"],
                        "original": product["price"]["original"],
                        "text": product["price"]["text"]
                    }
                ],
                "rating": product["rating"],
                "shop": [
                    {
                        "id": product["shop"]["id"],
                        "name": product["shop"]["name"],
                        "url": product["shop"]["url"],
                        "tier": product["shop"]["tier"],
                        "city": product["shop"]["city"]
                    }
                ],
                "image": product["url"]
            })

        return result

