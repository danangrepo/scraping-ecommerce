from flask import Flask, request, jsonify
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor
from scrape.tokopedia import Tokopedia
from utils.response_format import ResponseFormat

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=3)

@app.route("/scrape", methods=["GET"])
def get_scraped_data():
    try :
        query = request.args.get("query", "")
        page = request.args.get("page", "1")
        filter = request.args.get("filter", "")
    
        if not query:
            return ResponseFormat(
                code=400,
                message="Bad Request",
                error="Query parameter is required",
                data=[]
            ).error()
        
        tokopedia = Tokopedia(query, page, filter)
        future = executor.submit(tokopedia.sync_scrape_data)
        data = future.result()
        response = tokopedia.get_product(data)
        return ResponseFormat(
            code=200,
            message="Success",
            query=query,
            page=page,
            data=response,
            total=len(response)
        ).success()
    except Exception as e:
        return ResponseFormat(
            code=500,
            message="Internal Server Error",
            error=str(e),
            data=[]
        ).error()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=9000)

