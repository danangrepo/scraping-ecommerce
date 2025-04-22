import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import os
import re
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

        self.url = f"{self.url}/search?ob={self.filter['ob']}&page={self.page}&q={self.query}&st=product&navsource="

    
    async def go_to_page(self, page, page_number):
        print("go to page")
        try:
            pagination_btn = await page.query_selector(f'button[aria-label="Laman {page_number}"]')
            if pagination_btn:
                await pagination_btn.click()
                await asyncio.sleep(3)
                print(f"✅ Berhasil pindah ke halaman {page_number}")
            else:
                print(f"⚠️ Tombol halaman {page_number} tidak ditemukan.")
        except Exception as e:
            print(f"⚠️ Gagal klik halaman {page_number}: {e}")
 
    async def scroll_page(self, page, max_scrolls=5):
        for _ in range(max_scrolls):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def sync_scrape_data(self):
        """Menjalankan Playwright dalam event loop tersendiri."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.processScrape())
    
    async def processScrape(self):
        """Fungsi async untuk scraping menggunakan Playwright"""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            tabPage = await browser.new_page()

            # add promo produk
            async def handle_response(response):
                if self.endpoint_product in response.url:
                    self.data = []
                    json_data = await response.json()
                    self.data.append(json_data)

            # Pasang listener sebelum membuka halaman
            tabPage.on("response", lambda response: asyncio.create_task(handle_response(response)))
            await tabPage.goto(self.url)
            
            await tabPage.click("//button[contains(@data-unify, 'Select')]", timeout=500)
            await asyncio.sleep(1)
            best_match_option = await tabPage.query_selector(f'button[data-item-text="Paling Sesuai"]')
            await best_match_option.click()
            await asyncio.sleep(1)

            if int(self.page) > 1:
                await self.scroll_page(tabPage, max_scrolls=2)
                await asyncio.sleep(1)
                await self.go_to_page(tabPage, self.page)
                await asyncio.sleep(1)
                
            await browser.close()
            return self.data
        
    def get_product(self, data=[]):
        output = []
        response = data[0][0]["data"]["searchProductV5"]["data"]["products"]
        for i, product in enumerate(response):
            sold = "0"
            for group in product.get("labelGroups", []):
                title = group.get("title", "")
                match = re.search(r"(\d+)", title)
                if match:
                    sold = match.group(1)
                    break 

            priceOriginal = product["price"]["original"] if product["price"]["original"] else "0"
            output.append({
                "id": product["id"],
                "url": product["url"],
                "media_url": [
                    product["mediaURL"]["image"],
                    product["mediaURL"]["image300"],
                    product["mediaURL"]["videoCustom"]
                ],
                "name": product["name"],
                "sold": sold,
                "price": {
                    "discount_percentage": product["price"]["discountPercentage"],
                    "number": product["price"]["number"],
                    "original_number": int(priceOriginal.replace("Rp", "").replace(" ", "").replace(".", "")),
                    "original_text": priceOriginal,
                    "text": product["price"]["text"]
                },
                "rating": product["rating"],
                "shop": {
                    "id": product["shop"]["id"],
                    "name": product["shop"]["name"],
                    "url": product["shop"]["url"],
                    "tier": product["shop"]["tier"],
                    "city": product["shop"]["city"]
                }
            })

        result = {
            "result": output,
            "total_data": str(data[0][0]["data"]["searchProductV5"]["header"]["totalData"]),
            "page_size": str(len(output))
        }
        return result

