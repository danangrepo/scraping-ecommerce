import asyncio
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=3)  # Maksimal 3 request paralel

def sync_scrape_data(query, page="1", filter=""):
    """Menjalankan Playwright dalam event loop tersendiri."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(playwright_scrape(query, page, filter))

async def go_to_page(page, page_number):
    """Klik tombol halaman tertentu di pagination"""
    try:
        pagination_btn = await page.query_selector(f'button[aria-label="Laman {page_number}"]')
        if pagination_btn:
            await pagination_btn.click()
            await asyncio.sleep(3)  # Tunggu setelah klik agar data termuat
            print(f"✅ Berhasil pindah ke halaman {page_number}")
        else:
            print(f"⚠️ Tombol halaman {page_number} tidak ditemukan.")
    except Exception as e:
        print(f"⚠️ Gagal klik halaman {page_number}: {e}")

async def scroll_page(page, max_scrolls=5):
    """Melakukan scroll ke bawah beberapa kali agar lebih banyak produk termuat."""
    for _ in range(max_scrolls):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)  # Tunggu agar data baru termuat

async def playwright_scrape(query: str, page: str, filter=""):
    """Fungsi async untuk scraping menggunakan Playwright"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        tabPage = await browser.new_page()

        all_products = []
        async def handle_response(response):
            if "graphql/SearchProductV5Query" in response.url:
                print("✅ Menemukan GraphQL Request!")
                json_data = await response.json()
                all_products.append(json_data)

        # Pasang listener sebelum membuka halaman
        tabPage.on("response", lambda response: asyncio.create_task(handle_response(response)))

        url = "https://www.tokopedia.com/"
        if int(page) > 1:
            pageBefore = int(page) - 1
            url = f"https://www.tokopedia.com/search?ob={filter}&page={pageBefore}&q={query}&st=product&navsource="

        await tabPage.goto(url)
        
        if int(page) == 1:
            search_box = await tabPage.wait_for_selector('input[aria-label="Cari di Tokopedia"]')
            await search_box.fill(query)
            print(f"📝 Mengetik: {query}")
            # Tekan tombol "Enter" untuk memicu pencarian
            await search_box.press("Enter")
            print("⏎ Menekan Enter untuk mencari...")
            await asyncio.sleep(5)

        print("Url yang dibuka:", url)
        print("🔍 Mencari produk di page", page)
        if int(page) > 1:
            await scroll_page(tabPage, max_scrolls=2)
            await asyncio.sleep(2)
            await go_to_page(tabPage, page)
            await asyncio.sleep(2)

        await browser.close()
        return all_products

@app.route("/scrape", methods=["GET"])
def get_scraped_data():
    try :
        query = request.args.get("query", "")
        page = request.args.get("page", "")
        filter = request.args.get("filter", "")

        if not page:
            page = "1"

        if not query:
            return jsonify({
                'code': 400,
                'message': 'Bad Request',
                "error": "Query parameter is required",
                "data": []
            }), 400
        
        future = executor.submit(sync_scrape_data, query, page, filter)
        data = future.result()

        response = []
        for i, product in enumerate(data[0][0]["data"]["searchProductV5"]["data"]["products"]):
            response.append({
                "id": product["id"],
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

        return jsonify({
            "code": 200,
            "message": "Success",
            "query": query,
            "page": page,
            "data": response,
            "total": len(response)
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': 'Internal Server Error',
            "error": str(e),
            "data": []
        }), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=9000)
