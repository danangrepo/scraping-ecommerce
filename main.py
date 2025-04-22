from flask import Flask, request, jsonify
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor
from scrape.tokopedia import Tokopedia
from scrape.blibli import Blibli
from scrape.lazada import Lazada
from scrape.shopee import Shopee
from utils.response_format import ResponseFormat
import traceback

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=3)

@app.route("/scrape", methods=["GET"])
def get_scraped_data():
    try :
        query = request.args.get("query", "")
        page = request.args.get("page", "1")
        filter = request.args.get("filter", "")
        ecommerce = request.args.get("ecommerce", "")
        if not query:
            return ResponseFormat(
                code=400,
                message="Bad Request",
                error="Query parameter is required",
                data=[]
            ).error()
        
        if (ecommerce == "tokopedia"): 
            platform = Tokopedia(query, page, filter)
            future = executor.submit(platform.sync_scrape_data)
        elif (ecommerce == "blibli"):
            platform = Blibli(query, page, filter)
            future = executor.submit(platform.sync_scrape_data)
        elif (ecommerce == "lazada"):
            platform = Lazada(query, page, filter)
            future = executor.submit(platform.sync_scrape_data)
        elif (ecommerce == "shopee"):
            platform = Shopee(query, page, filter)
            future = executor.submit(platform.sync_scrape_data)
        
        data = future.result()
        print("data")
        print(len(data))
        response = platform.get_product(data)
        
        return ResponseFormat(
            code=200,
            message="Success",
            query=query,
            page=page,
            data=response["result"],
            page_size=response["page_size"],
            total_data=response["total_data"]
        ).success()
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Error: {str(e)}\nDetail:\n{error_detail}")

        return ResponseFormat(
            code=500,
            message="Internal Server Error",
            error=str(e),
            data=[]
        ).error()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=9000)

