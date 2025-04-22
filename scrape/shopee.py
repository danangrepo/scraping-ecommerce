import asyncio
import undetected_chromedriver as uc
import json
import sys
import os
import re
import pickle
import time

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
load_dotenv()

# create class tokopedia
class Shopee:
    def __init__(self, query = "", page="1", filter="best-match"):
        self.url = os.getenv("SHOPEE_URL")
        self.endpoint_product = os.getenv("SHOPEE_ENDPOINT_PRODUCT")
        self.query = query
        self.page = page
        self.data = []
        self.filter_data = [
            {
                "name": "Paling Sesuai",
                "value": "best-match",
                "ob": "relevancy"
            },
            {
                "name": "Terbaru",
                "value": "newest",
                "ob": "ctime"
            },
            {
                "name": "Harga Terendah",
                "value": "asc",
                "ob": "price"
            },
            {
                "name": "Harga Tertinggi",
                "value": "desc",
                "ob": "price"
            },
            {
                "name": "Ulasan",
                "value": "rating",
                "ob": "sales"
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

        self.url = f"{self.url}/search?keyword={self.query}&page={self.page}&sortBy={self.filter["ob"]}"
        if (self.filter["ob"] == "price"):
            self.url += f"&order={self.filter["value"]}"

    def sync_scrape_data(self):
        """Menjalankan Playwright dalam event loop tersendiri."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.processScrape())
    
    async def processScrape(self):
        """Fungsi async untuk scraping menggunakan Playwright"""
        driver = self.init_driver()
        driver.get(self.url)
        self.load_cookies(driver)
        
        wait = WebDriverWait(driver, 10)
        while True:
            time.sleep(3)
            
            login_button = driver.find_elements(By.XPATH, "//button[contains(text(), 'Log in')]")
            captcha_identify = driver.find_elements(By.XPATH, "//h1[contains(text(), 'Verifikasi untuk melanjutkan')]")
            verification_identify = driver.find_elements(By.XPATH, "//button[@aria-label='Verifikasi melalui link']")
            retry_identify = driver.find_elements(By.XPATH, "//button[contains(text(), 'Coba Lagi')]")
            back_button = driver.find_elements(By.XPATH, "//button[contains(text(), 'Kembali ke Halaman Utama')]")
            
            if login_button:
                print("Halaman Login Terdeteksi")
                driver.find_element(By.NAME, "loginKey").send_keys(os.getenv("SHOPEE_USERNAME"))
                time.sleep(1)
                driver.find_element(By.NAME, "password").send_keys(os.getenv("SHOPEE_PASSWORD"))
                time.sleep(1)
                driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]").click()
                time.sleep(2)
            elif captcha_identify:
                print("Halaman Captcha Terdeteksi")
                time.sleep(10)
            elif verification_identify:
                print("Halaman Verifikasi Akun")
                verification_identify[0].click()
                time.sleep(3)
                driver.find_element(By.XPATH, "//button[contains(text(), 'OK')]").click()
                time.sleep(15)
            elif retry_identify:
                max_retry = 3
                attempt = 0
                refresh = False
                while attempt <= max_retry:
                    try:
                        retry_button = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Coba Lagi')]")))
                        if retry_button.is_displayed():
                            print("Halaman Coba Lagi")
                            retry_button.click()

                            time.sleep(3)
                            driver.execute_cdp_cmd("Network.clearBrowserCache", {})
                            driver.execute_script("location.reload(true);")
                            attempt += 1
                            if (attempt < max_retry - 1):
                                refresh = True
                                driver.execute_script("window.location.href = 'https://shopee.co.id'")
                            elif refresh:
                                break
                        else:
                            print("Tombol 'Coba Lagi' tidak ditemukan.")
                    except:
                        print("Tombol 'Coba Lagi' tidak ditemukan.")
            elif back_button:
                print("Kembali ke Halaman Utama")
                back_button[0].click()
                driver.execute_script(f"window.location.href = '{self.url}'")
                time.sleep(5)
            else:
                try:
                    search_form = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "shopee-searchbar")))
                    if search_form.is_displayed():
                        print("Search Form is displayed")
                        self.save_cookies(driver)
                        
                        print("Scraping data...")
                    	
                        log_entries = driver.get_log("performance")
                        for entry in log_entries:
                            try:
                                message_obj = json.loads(entry.get("message"))
                                message = message_obj.get("message")
                                method = message.get("method")
                                if method == 'Network.responseReceived':
                                    response_url = message.get('params',{}).get('response',{}).get('url','')
                                    request_id = message.get('params', {}).get('requestId', '')
                                    
                                    if self.endpoint_product in response_url:
                                        self.data = []
                                        response = driver.execute_cdp_cmd('Network.getResponseBody',{'requestId':request_id})
                                        response_body = response.get('body','')
                                        self.data.append(response_body)
                                        # save response to file
                                        with open("contoh.txt", "w", encoding="utf-8") as file:
                                            file.write(response_body)
                                            file.close()
                                        break
                            except Exception as e:
                                print(e)

                        # for log in logs:
                        #     if self.endpoint_product in log:
                        #         print(log)

                        break
                except Exception as e:
                    print(f"Error: {e}")
                    break
    
        driver.quit()
        return self.data

    def init_driver(self):
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument('--enable-logging')
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        driver = uc.Chrome(options=options)
        driver.execute_cdp_cmd("Network.enable", {})

        return driver
    
    def save_cookies(self, driver, filename="cookies.pkl"):
        cookies = driver.get_cookies()  
        if cookies:  # Pastikan ada cookies sebelum menyimpan
            with open(filename, "wb") as file:
                pickle.dump(cookies, file)
            print("Cookies berhasil disimpan.")
        else:
            print("Tidak ada cookies yang disimpan.")

    def load_cookies(self, driver, filename="cookies.pkl"):
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            print("Cookie file tidak ditemukan atau kosong, silakan login ulang.")
            return

        try:
            with open(filename, "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            print("Cookies berhasil dimuat.")
        except (pickle.UnpicklingError, EOFError) as e:
            print(f"Error loading cookies: {e}. File corrupt, menghapus file...")
            os.remove(filename)  # Hapus file jika corrupt
        
    def get_product(self, data=[]):
        output = []

        dataParsing = json.loads(data[0])
        response = dataParsing["items"]

        for i, product in enumerate(response):
            priceOriginal = product["item_basic"]["price_before_discount"] // 100000
            priceDisplay = product["item_basic"]["price"] // 100000
            mediaUrl = []
            for media in product["item_basic"]["images"]:
                mediaUrl.append(f"https://down-id.img.susercontent.com/file/{media}")

            output.append({
                "id": str(product["item_basic"]["itemid"]),
                "url": "https://shopee.co.id/" + re.sub(r"[ /|+]+", "-", product["item_basic"]["name"]) + "-i." + str(product["item_basic"]["shopid"]) + "." + str(product["item_basic"]["itemid"]),
                "media_url": mediaUrl,
                "name": product["item_basic"]["name"],
                "sold": str(product["item_basic"]["global_sold_count"]),
                "price": {
                    "discount_percentage": 0 if product["item_basic"]["discount"] is None else int(product["item_basic"]["discount"].replace("%", "")),
                    "number": priceDisplay,
                    "original_number": priceOriginal,
                    "original_text": f"Rp{priceOriginal:,}".replace(",", "."),
                    "text": f"Rp{priceDisplay:,}".replace(",", ".")
                },
                "rating": str(round(product["item_basic"]["item_rating"]["rating_star"], 1)),
                "shop": {
                    "id": str(product["item_basic"]["shopid"]),
                    "name": product["item_basic"]["shop_name"],
                    "url": "",
                    "tier": "",
                    "city": product["item_basic"]["shop_location"]
                }
            
            })

        result = {
            "result": output,
            "total_data": str(dataParsing["total_count"]),
            "page_size": str(len(output))
        }
        return result

