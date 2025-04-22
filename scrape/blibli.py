import asyncio
from playwright.async_api import async_playwright
import undetected_chromedriver as uc
from dotenv import load_dotenv
import os
load_dotenv()

# create class blibli
class Blibli:
    def __init__(self, query = "", page="1", filter="best-match"):
        self.url = os.getenv("BLIBLI_URL")
        self.endpoint_product = os.getenv("BLIBLI_ENDPOINT_PRODUCT")
        self.query = query
        self.page = page
        self.page = 0
        self.perPage = 40
        self.start = self.perPage * (self.page - 1) if self.page > 1 else 0 
        self.data = []
        self.filter_data = [
            {
                "name": "Paling Sesuai",
                "value": "best-match",
                "ob": 0
            },
            {
                "name": "Terbaru",
                "value": "newest",
                "ob": 1
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
                "ob": 7
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

        self.url = f"{self.url}/{self.endpoint_product}?searchTerm={self.query}&page={self.page}&start={self.start}&merchantSearch=true&multiCategory=true&intent=true&channelId=web&showFacet=false&sort={self.filter['ob']}"

    def sync_scrape_data(self):
        """Menjalankan Playwright dalam event loop tersendiri."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.processScrape())
    
    async def processScrape(self):
        """Fungsi async untuk scraping menggunakan Playwright"""
        browser = uc.Chrome(use_subprocess=True)  # Start browser
        browser.get(self.url)

        script = """
            return fetch(arguments[0])
                .then(response => response.json())
                .then(data => data);
        """
        try:
            json_data = browser.execute_script(script, self.url)
            self.data.append(json_data)
        except Exception as e:
            print(f"Error mengambil data: {e}")

        browser.quit()
        return self.data
        
    def get_product(self, data=[]):
        output = []
        response = data[0]["data"]["products"]
        for i, product in enumerate(response):
            priceOriginal = product["price"].get("strikeThroughPriceDisplay", product["price"]["priceDisplay"])
            

            output.append({
                "id": product["id"],
                "url": f"{os.getenv("BLIBLI_URL")}{product["url"]}",
                "media_url": product["images"],
                "name": product["name"],
                "sold": str(product.get("soldCountTotal", 0)),
                "price": {
                    "discount_percentage": product["price"]["discount"],
                    "number": product["price"]["minPrice"],
                    "original_number": int(priceOriginal.replace("Rp", "").replace(" ", "").replace(".", "")),
                    "original_text": priceOriginal,
                    "text": product["price"]["priceDisplay"]
                },
                "rating": str(product["review"]["rating"]),
                "shop": {
                    "id": product["merchantCode"],
                    "name": product["merchantName"],
                    "url": "",
                    "tier": "",
                    "city": product["location"]
                }
            })

        result = {
            "result": output,
            "total_data": str(data[0]["data"]["paging"]["total_item"]),
            "page_size": str(data[0]["data"]["paging"]["item_per_page"])
        }
        return result

