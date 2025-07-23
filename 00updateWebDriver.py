import os
import re
import zipfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
import urllib.request
import requests
from bs4 import BeautifulSoup
import configparser
import logging
import logzero
from logzero import logger

### 設定値取得 ###
config = configparser.ConfigParser()
config.read("settings.ini", "utf-8")
log_file = config["LOG"]["path"]
WEBDRIVER_BASE_URL = config["WEBDRIVER"]["WEBDRIVER_BASE_URL"]
LATEST_VERSION_URL = config["WEBDRIVER"]["LATEST_VERSION_URL"]

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

# WebDriverを起動する
def isLaunch(chromedriver_path='chromedriver.exe'):
    service = Service(executable_path=chromedriver_path)
    try:
        driver = webdriver.Chrome(service=service)
        logger.info('WebDriverの起動に成功しました。問題ありません。')
        driver.quit()
        return True
    except (FileNotFoundError, WebDriverException, SessionNotCreatedException) as e:
        logger.error(f"WebDriverの起動に失敗しました。エラー詳細: {str(e)}")
        return e

# 最新のWebDriverのバージョンを取得する関数
def get_latest_webdriver_version():
    try:
        response = requests.get(LATEST_VERSION_URL)
        response.raise_for_status() # HTTPエラーがあれば例外を発生させる
        soup = BeautifulSoup(response.content, 'html.parser')

        td_element = soup.find(string="Stable").find_next('td')
        stable_version = td_element.find("code").text
        logger.info(f"最新のWebDriver安定版バージョン: {stable_version}")
        return stable_version
    except requests.exceptions.RequestException as e:
        logger.error(f"最新のWebDriverバージョン取得中にエラーが発生しました: {e}")
        return None
    except AttributeError:
        logger.error("HTML構造が変更されたか、安定版バージョンが見つかりませんでした。")
        return None

# 指定されたバージョンのWebDriverをダウンロードする関数
def download_webdriver_version(version):
    file_url = f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{version}/win32/chromedriver-win32.zip"
    save_path = "./download_webdriver.zip"
    logger.info(f'{version} のWebDriverをダウンロードします。')
    try:
        # zipファイルをダウンロード
        with urllib.request.urlopen(file_url) as download_file:
            data = download_file.read()
            with open(save_path, mode='wb') as save_file:
                save_file.write(data)
        # ダウンロードしたzipファイルを解凍
        with zipfile.ZipFile("./download_webdriver.zip") as obj_zip:
            with obj_zip.open('chromedriver-win32/chromedriver.exe') as src, open('./chromedriver.exe', 'wb') as dst:
                dst.write(src.read())
        # zipファイルはいらないので削除 
        os.remove('./download_webdriver.zip')
        logger.info("WebDriverのダウンロードと解凍が完了しました。")
        return True
    except Exception as e:
        logger.error(f"WebDriverのダウンロードまたは解凍中にエラーが発生しました: {e}")
        return False

# WebDriverのダウンロードと起動を試みる関数
def download_and_launch_webdriver(error_obj):
    # エラーメッセージから現在のバージョンを取得
    match = re.search(r'(?<=\bchrome=)\d+', str(error_obj))
    if match:
        current_version = match.group()
        logger.info(f"エラーメッセージからChromeのバージョンを検出しました: {current_version}")
    else:
        logger.warning("エラーメッセージからChromeのバージョンを取得できませんでした。最新のバージョンを取得します。")
        current_version = get_latest_webdriver_version()
        if not current_version:
            logger.error("最新のWebDriverのバージョンを取得できませんでした。処理を終了します。")
            return

    # バージョン情報の取得とダウンロード
    if download_webdriver_version(current_version):
        if isLaunch() is True:
            logger.info("WebDriverの更新と起動に成功しました。")
        else:
            logger.error("更新後のWebDriverの起動に失敗しました。")
    else:
        logger.error("WebDriverのダウンロードに失敗したため、起動を試みません。")

# 以下、メインの実行部分
try:
    logger.info('*** 00 updateWebDriver START ***')
    error = isLaunch()
    if isinstance(error, (SessionNotCreatedException, FileNotFoundError, WebDriverException)):
        download_and_launch_webdriver(error)
    elif error is not True:
        logger.error(f"その他のエラーが発生しました: {str(error)}")

except Exception as e:
    logger.error(f'予期せぬエラーが発生しました: {e}')
    sys.exit(1)

finally:
    logger.info('*** 00 updateWebDriver END ***')
