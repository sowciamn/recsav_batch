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
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback
from selenium.webdriver.common.keys import Keys

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

### Chromeドライバのパス設定 ###
chromedriver_path = config["WEBDRIVER"]["chrome_driver"]

### 履歴の検索対象日 ###
today = datetime.today()
if arg_today is not None:
    today = arg_today
target_month = today - relativedelta(months=1)

try:
    logger.info('*** 01 createRakutenCardCsv START ***')

    ### Chromeドライバを生成 ###
    services = Service(executable_path=chromedriver_path)

    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    options.add_argument("enable-automation")
    # options.add_argument("--headless")
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
    driver = webdriver.Chrome(service=services, options=options)

    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(output_file):
        os.remove(output_file)

    ### 楽天e-NAVIへログイン ###
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    # ユーザーID入力フィールド
    elem = wait.until(EC.element_to_be_clickable((By.ID, "user_id")))
    elem.clear()
    elem.send_keys(user)

    # 最初の「次へ」ボタン
    wait.until(EC.element_to_be_clickable((By.ID, "cta001"))).click()

    # パスワード入力フィールド
    elem = wait.until(EC.element_to_be_clickable((By.ID, "password_current")))
    elem.clear()
    elem.click()
    elem.send_keys(password)
    elem.send_keys(Keys.TAB)
    elem.send_keys(Keys.TAB)
    elem.send_keys(Keys.ENTER)

    # ログイン処理の完了を待つ
    time.sleep(5)

    ### CSVをダウンロード ###
    driver.get("https://www.rakuten-card.co.jp/e-navi/members/statement/index.xhtml")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".stmt-c-btn-dl.stmt-csv-btn"))).click()

    ### ダウンロードしたCSVをリネーム ###
    # ファイル名が 'enaviYYYYMM(9814).csv' のような形式を想定
    download_pattern = os.path.join(output_dir, 'enavi*.csv')
    download_files = []
    # ダウンロードが完了するまで最大30秒待機
    for _ in range(30):
        download_files = glob.glob(download_pattern)
        if download_files:
            time.sleep(5)
            break
        time.sleep(1)

    if download_files:
        latest_file = max(download_files, key=os.path.getctime)
        os.rename(latest_file, output_file)
        logger.info(f"CSVファイルをリネームしました: {latest_file} -> {output_file}")
    else:
        logger.warning("ダウンロードされたCSVファイルが見つかりませんでした。")


except Exception as e:
    logger.error('Exception Error: %s' % e)
    logger.error(traceback.format_exc())
    sys.exit(1)

finally:
    driver.quit()
    logger.info('*** 01 createRakutenCardCsv END ***')