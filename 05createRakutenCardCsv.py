import os
import shutil
import glob
import sys
import configparser
import csv
import time
import logging
import logzero
from logzero import logger
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

### 引数取得 ###
args = sys.argv
arg_today = None
if len(args) > 1:
    arg_today = datetime.strptime(args[1] + ' 00:00:00', '%Y-%m-%d %H:%M:%S')

### 設定値取得 ###
config = configparser.ConfigParser()
config.read("settings.ini", "utf-8")
url = config["RAKUTEN"]["url"]
user = config["RAKUTEN"]["user"]
password = config["RAKUTEN"]["password"]
history_csv = config["RAKUTEN"]["history_csv"]
output_dir = config["OUTPUT"]["dir"]
log_file = config["LOG"]["path"]
chrome_bin = config["BINARY"]["chrome_bin"]
chrome_driver = config["BINARY"]["chrome_driver"]

### ログ設定 ###
logger = logzero.setup_logger(
    name='logzero',
    logfile=log_file,
    level=20,
    formatter=logging.Formatter(
        '[%(levelname)s %(asctime)s] %(message)s'),
    maxBytes=10240,
    backupCount=3,
    fileLoglevel=20,
    disableStderrLogger=False
)

### CSV設定 ###
output_file = os.path.join(output_dir, history_csv)

### 履歴の検索対象日 ###
today = datetime.today()
if arg_today is not None:
    today = arg_today
target_month = today - relativedelta(months=1)

try:
    logger.info('*** 05 createRakutenCardCsv START ***')
    logger.info('対象月：' + datetime.strftime(target_month, "%Y%m"))

    ### Chromeドライバを生成 ###
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    options.add_argument("enable-automation")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-infobars")
    options.add_argument('--disable-extensions')
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-browser-side-navigation")
    options.add_argument("--disable-gpu")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_experimental_option("prefs", {
        "download.default_directory": output_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "profile.default_content_setting_values.notifications" : 2,
        "safebrowsing.enabled": True
    })
    driver = webdriver.Chrome(options=options)

    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(output_file):
        os.remove(output_file)

    ### 楽天e-NAVIへログイン ###
    driver.get(url)
    time.sleep(5)
    elem = driver.find_element(By.ID, "u")
    elem.clear()
    elem.send_keys(user)
    elem = driver.find_element(By.ID, "p")
    elem.clear()
    elem.send_keys(password)
    driver.find_element(By.NAME, "login").click()
    time.sleep(5)

    ### CSVをダウンロード ###
    driver.get("https://www.rakuten-card.co.jp/e-navi/members/statement/index.xhtml")
    time.sleep(5)
    
    # CSVダウンロードボタンをクリック
    driver.find_element(By.ID, "csv-output").click()
    time.sleep(5)

    ### ダウンロードしたCSVをリネーム ###
    # ファイル名が 'card_meisai_YYYYMMDDHHMMSS.csv' のような形式を想定
    download_files = glob.glob(os.path.join(output_dir, 'card_meisai_*.csv'))
    if download_files:
        latest_file = max(download_files, key=os.path.getctime)
        os.rename(latest_file, output_file)
        logger.info(f"CSVファイルをリネームしました: {latest_file} -> {output_file}")
    else:
        logger.warning("ダウンロードされたCSVファイルが見つかりませんでした。")


except Exception as e:
    logger.error('Exception Error: %s' % e)
    sys.exit(1)

finally:
    driver.quit()
    logger.info('*** 05 createRakutenCardCsv END ***')