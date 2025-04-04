import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import os
import re
import requests
load_dotenv()

# create class tokopedia
class Lazada:
    def __init__(self, query = "", page="1", filter="best-match"):
        self.url = os.getenv("LAZADA_URL")
        self.endpoint_product = os.getenv("LAZADA_ENDPOINT_PRODUCT")
        self.query = query
        self.page = page
        self.data = []
        self.filter_data = [
            {
                "name": "Paling Sesuai",
                "value": "best-match",
                "ob": "popularity"
            },
            {
                "name": "Terbaru",
                "value": "newest",
                "ob": "popularity"
            },
            {
                "name": "Harga Terendah",
                "value": "price-asc",
                "ob": "priceasc"
            },
            {
                "name": "Harga Tertinggi",
                "value": "price-desc",
                "ob": "pricedesc"
            },
            {
                "name": "Ulasan",
                "value": "rating",
                "ob": "popularity"
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

        self.url = f"{self.url}/catalog/?ajax=true&isFirstRequest=true&page={self.page}&q={self.query}&sort={self.filter["ob"]}"

    def sync_scrape_data(self):
        """Menjalankan Playwright dalam event loop tersendiri."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.processScrape())
    
    async def processScrape(self):
        """Fungsi async untuk scraping menggunakan Playwright"""
        url = self.url
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            self.data.append(response.json())
        else:
            print(f"Request gagal, status code: {response.status_code}")
        
        return self.data
        
    def get_product(self, data=[]):
        output = []
        response = data[0]["mods"]["listItems"]
        for i, product in enumerate(response):
            sold = re.search(r"(\d+)", product.get("itemSoldCntShow", "0"))
            sold = sold.group(1)
            originalPrice = int(product.get("originalPrice", product.get("price")))

            output.append({
                "id": product["nid"],
                "url": product["itemUrl"],
                "media_url": [
                    product["image"],
                ],
                "name": product["name"],
                "sold": sold,
                "price": [
                    {
                        "discount_percentage": round(((originalPrice - int(product["price"])) / originalPrice) * 100, 1),
                        "number": int(product["price"]),
                        "original_number": originalPrice,
                        "original_text": f"Rp{originalPrice:,}".replace(",", "."),
                        "text": product["priceShow"].replace(",",".")
                    }
                ],
                "rating": product["ratingScore"],
                "shop": [
                    {
                        "id": product["sellerId"],
                        "name": product["sellerName"],
                        "url": "",
                        "tier": "",
                        "city": product["location"]
                    }
                ]
            })
        
        result = {
            "result": output,
            "total_data": data[0]["mainInfo"]["totalResults"],
            "page_size": data[0]["mainInfo"]["pageSize"]
        }
        return result

