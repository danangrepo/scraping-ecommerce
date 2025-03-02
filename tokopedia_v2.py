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

        url = f"https://www.tokopedia.com/search?ob={filter}&page={page}&q={query}&st=product&navsource="
        await tabPage.goto(url, timeout=5000)

        await tabPage.click("//button[contains(@data-unify, 'Select')]")
        await asyncio.sleep(1)
        best_match_option = await tabPage.query_selector(f'button[data-item-text="Paling Sesuai"]')
        await best_match_option.click()
        await asyncio.sleep(1)

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

