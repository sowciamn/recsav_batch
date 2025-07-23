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
config.read("settings.ini")
url = config["ZAIM"]["url"]
user = config["ZAIM"]["user"]
password = config["ZAIM"]["password"]
history_csv = config["ZAIM"]["history_csv"]
output_dir = config["OUTPUT"]["dir"]
log_file = config["LOG"]["path"]
money_url = config["ZAIM_MONEY"]["url"]
chrome_bin = config["BINARY"]["chrome_bin"]
chrome_driver = config["BINARY"]["chrome_driver"]

### ログ設定 ###
logger = logzero.setup_logger(
    # loggerの名前、複数loggerを用意するときに区別できる
    name='logzero',
    # ログファイルの格納先
    logfile=log_file,
    # 標準出力のログレベル
    level=20,
    formatter=logging.Formatter(
        '[%(levelname)s %(asctime)s] %(message)s'),    # ログのフォーマット
    # ログローテーションする際のファイルの最大バイト数
    maxBytes=10240,
    # ログローテーションする際のバックアップ数
    backupCount=3,
    # ログファイルのログレベル
    fileLoglevel=20,
    # 標準出力するかどうか
    disableStderrLogger=False
)

### CSV設定 ###
output_file = os.path.join(output_dir, history_csv)

### 履歴の検索対象日 ###
# 本日
today = datetime.today()
if arg_today is not None:
    today = arg_today
# 先月
one_month_ago = today - relativedelta(months=1)
# 先々月
two_month_ago = today - relativedelta(months=2)
# 開始日（先々月の1日）
start_date = two_month_ago.replace(day=1)
# 終了日（先月の末日）
end_date = (today + relativedelta(months=1)).replace(day=1) - timedelta(days=1)

try:
    logger.info('*** 01 createCsvForZaim START ***')
    logger.info('対象月：' + datetime.strftime(start_date, "%Y%m") + '～' + datetime.strftime(
        end_date, "%Y%m"))

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

    # ダウンロードするファイルと同じ名称のファイルがある場合に削除する
    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(output_file):
        os.remove(output_file)

    ### Zaimへログイン ###
    driver.get(url)
    elem = driver.find_element(By.ID, "UserEmail")
    elem.clear()
    elem.send_keys(user)
    elem = driver.find_element(By.ID, "UserPassword")
    elem.clear()
    elem.send_keys(password)
    elem.submit()

    ### CSVをダウンロード ###
    time.sleep(5)
    money_url = money_url
    driver.get(money_url)
    time.sleep(5)

    elem = driver.find_element(By.XPATH, "//*[text()=\"Zaim の記録データをダウンロードする\"]")
    driver.execute_script('arguments[0].click();', elem)

    elem = driver.find_element(By.ID, "MoneyStartDateYear")
    select_elem = Select(elem)
    select_elem.select_by_value(datetime.strftime(start_date, "%Y"))

    elem = driver.find_element(By.ID, "MoneyStartDateMonth")
    select_elem = Select(elem)
    select_elem.select_by_value(datetime.strftime(start_date, "%m"))

    elem = driver.find_element(By.ID, "MoneyStartDateDay")
    select_elem = Select(elem)
    select_elem.select_by_value(datetime.strftime(start_date, "%d"))

    elem = driver.find_element(By.ID, "MoneyEndDateYear")
    select_elem = Select(elem)
    select_elem.select_by_value(datetime.strftime(end_date, "%Y"))

    elem = driver.find_element(By.ID, "MoneyEndDateMonth")
    select_elem = Select(elem)
    select_elem.select_by_value(datetime.strftime(end_date, "%m"))

    elem = driver.find_element(By.ID, "MoneyEndDateDay")
    select_elem = Select(elem)
    select_elem.select_by_value(datetime.strftime(end_date, "%d"))

    elem = driver.find_element(By.ID, "MoneyCharset")
    select_elem = Select(elem)
    select_elem.select_by_value("utf8")

    elem = driver.find_element(By.XPATH, "//input[@value='この条件でダウンロード']")
    driver.execute_script('arguments[0].click();', elem)
    # elem.click()
    time.sleep(5)

    ### ダウンロードしたCSVをリネーム ###
    output_dir_list = glob.glob(output_dir + 'Zaim*.csv')
    for file in output_dir_list:
        os.rename(file, output_file)
        break

except Exception as e:
    logger.error('Exception Error: %s' % e)
    sys.exit(1)

finally:
    driver.quit()
    logger.info('*** 01 createCsvForZaim END ***')
