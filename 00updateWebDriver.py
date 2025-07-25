import os
import re
import zipfile
import sys
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
WEBDRIVER_BASE_URL = config["WEBDRIVER"]["webdriver_base_url"]
LATEST_VERSION_URL = config["WEBDRIVER"]["latest_version_url"]

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
    disableStderrLogger=False,
)

# WebDriverを起動する
def isLaunch(chromedriver_path='chromedriver.exe'):
    service = Service(executable_path=chromedriver_path)
    try:
        driver = webdriver.Chrome(service=service)
        logger.info('WebDriver launched successfully. No issues.')
        driver.quit()
        return True
    except (FileNotFoundError, WebDriverException, SessionNotCreatedException) as e:
        logger.error(f"Failed to launch WebDriver. Error details: {str(e)}")
        return e

# 最新のWebDriverのバージョンを取得する関数
def get_latest_webdriver_version():
    try:
        response = requests.get(LATEST_VERSION_URL)
        response.raise_for_status() # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')

        td_element = soup.find(string="Stable").find_next('td')
        stable_version = td_element.find("code").text
        logger.info(f"Latest stable WebDriver version: {stable_version}")
        return stable_version
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while fetching latest WebDriver version: {e}")
        return None
    except AttributeError:
        logger.error("HTML structure changed or stable version not found.")
        return None

# 指定されたバージョンのWebDriverをダウンロードする関数
def download_webdriver_version(version):
    file_url = f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{version}/win32/chromedriver-win32.zip"
    save_path = "./download_webdriver.zip"
    logger.info(f'Downloading WebDriver version {version}.')
    try:
        # Download zip file
        with urllib.request.urlopen(file_url) as download_file:
            data = download_file.read()
            with open(save_path, mode='wb') as save_file:
                save_file.write(data)
        # Extract downloaded zip file
        with zipfile.ZipFile("./download_webdriver.zip") as obj_zip:
            with obj_zip.open('chromedriver-win32/chromedriver.exe') as src, open('./chromedriver.exe', 'wb') as dst:
                dst.write(src.read())
        # Remove zip file
        os.remove('./download_webdriver.zip')
        logger.info("WebDriver download and extraction completed.")
        return True
    except Exception as e:
        logger.error(f"Error during WebDriver download or extraction: {e}")
        return False

# WebDriverのダウンロードと起動を試みる関数
def download_and_launch_webdriver(error_obj):
    # Get current version from error message
    match = re.search(r'(?<=\bchrome=)\d+', str(error_obj))
    if match:
        current_version = match.group()
        logger.info(f"Detected Chrome version from error message: {current_version}")
    else:
        logger.warning("Could not get Chrome version from error message. Fetching latest version.")
        current_version = get_latest_webdriver_version()
        if not current_version:
            logger.error("Could not get the latest WebDriver version. Exiting process.")
            return

    # Get version information and download
    if download_webdriver_version(current_version):
        if isLaunch() is True:
            logger.info("WebDriver updated and launched successfully.")
        else:
            logger.error("Failed to launch WebDriver after update.")
    else:
        logger.error("WebDriver download failed, not attempting to launch.")

# Main execution part
try:
    logger.info('*** 00 updateWebDriver START ***')
    error = isLaunch()
    if isinstance(error, (SessionNotCreatedException, FileNotFoundError, WebDriverException)):
        download_and_launch_webdriver(error)
    elif error is not True:
        logger.error(f"An unexpected error occurred: {str(error)}")

except Exception as e:
    logger.error(f'An unexpected error occurred: {e}')
    sys.exit(1)

finally:
    logger.info('*** 00 updateWebDriver END ***')