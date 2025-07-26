import os
import re
import zipfile
import sys
import requests
import urllib.request
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from logzero import logger
import common

# --- 定数 ---
CHROMEDRIVER_PATH = 'chromedriver.exe'
DOWNLOAD_ZIP_PATH = 'download_webdriver.zip'
EXTRACT_DRIVER_PATH = 'chromedriver-win32/chromedriver.exe'


def check_webdriver_launch(chromedriver_path=CHROMEDRIVER_PATH):
    """
    指定されたパスのWebDriverが正常に起動できるか確認します。

    Args:
        chromedriver_path (str, optional): 確認するWebDriverのパス。

    Returns:
        bool or Exception: 起動成功時はTrue、失敗時は発生した例外オブジェクト。
    """
    service = Service(executable_path=chromedriver_path)
    try:
        driver = webdriver.Chrome(service=service)
        logger.info('WebDriver launched successfully. No issues.')
        driver.quit()
        return True
    except (FileNotFoundError, WebDriverException, SessionNotCreatedException) as e:
        logger.error(f"Failed to launch WebDriver. Error details: {e}")
        return e


def get_latest_webdriver_version(latest_version_url):
    """
    最新の安定版WebDriverのバージョン番号を取得します。

    Args:
        latest_version_url (str): 最新バージョン情報が記載されたURL。

    Returns:
        str or None: バージョン番号。取得失敗時はNone。
    """
    try:
        response = requests.get(latest_version_url)
        response.raise_for_status()  # HTTPエラーの場合は例外を発生
        soup = BeautifulSoup(response.content, 'html.parser')

        # "Stable" の文字列が含まれるtd要素からバージョン番号を取得
        td_element = soup.find(string="Stable").find_next('td')
        stable_version = td_element.find("code").text
        logger.info(f"Latest stable WebDriver version: {stable_version}")
        return stable_version
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while fetching latest WebDriver version: {e}")
        return None
    except AttributeError:
        logger.error("Could not find the version number. The HTML structure of the page may have changed.")
        return None


def download_webdriver(version, webdriver_base_url):
    """
    指定されたバージョンのWebDriverをダウンロードし、展開します。

    Args:
        version (str): ダウンロードするWebDriverのバージョン。
        webdriver_base_url (str): WebDriverのダウンロード元ベースURL。

    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse。
    """
    # file_url = f"{webdriver_base_url}/{version}/win32/chromedriver-win32.zip"
    file_url = f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{version}/win32/chromedriver-win32.zip"
    logger.info(f'Downloading WebDriver version {version}.')
    try:
        # zipファイルをダウンロード
        with urllib.request.urlopen(file_url) as download_file:
            with open(DOWNLOAD_ZIP_PATH, mode='wb') as save_file:
                save_file.write(download_file.read())
        
        # zipファイルを展開してchromedriver.exeを取得
        with zipfile.ZipFile(DOWNLOAD_ZIP_PATH) as obj_zip:
            with obj_zip.open(EXTRACT_DRIVER_PATH) as src, open(CHROMEDRIVER_PATH, 'wb') as dst:
                dst.write(src.read())
        
        logger.info("WebDriver download and extraction completed.")
        return True
    except Exception as e:
        logger.error(f"Error during WebDriver download or extraction: {e}")
        return False
    finally:
        # zipファイルを削除
        if os.path.exists(DOWNLOAD_ZIP_PATH):
            os.remove(DOWNLOAD_ZIP_PATH)


def update_and_relaunch_webdriver(error_obj, latest_version_url, webdriver_base_url):
    """
    エラー情報から適切なWebDriverをダウンロードし、再起動を試みます。

    Args:
        error_obj (Exception): WebDriver起動時に発生した例外。
        latest_version_url (str): 最新バージョン情報が記載されたURL。
        webdriver_base_url (str): WebDriverのダウンロード元ベースURL。
    """
    # エラーメッセージから現在のChromeバージョンを正規表現で抽出
    match = re.search(r'(?<=\bchrome=)\d+', str(error_obj))
    if match:
        current_version = match.group()
        logger.info(f"Detected Chrome version from error message: {current_version}")
    else:
        logger.warning("Could not get Chrome version from error message. Fetching latest version.")
        current_version = get_latest_webdriver_version(latest_version_url)
        if not current_version:
            logger.error("Could not get the latest WebDriver version. Exiting process.")
            return

    # 新しいWebDriverをダウンロードして起動確認
    if download_webdriver(current_version, webdriver_base_url):
        if check_webdriver_launch():
            logger.info("WebDriver updated and launched successfully.")
        else:
            logger.error("Failed to launch WebDriver after update.")
    else:
        logger.error("WebDriver download failed, not attempting to launch.")


def main():
    """
    メイン処理
    """
    try:
        # --- 初期設定 ---
        config = common.load_config()
        common.setup_logger(config["LOG"]["path"])
        webdriver_base_url = config["WEBDRIVER"]["webdriver_base_url"]
        latest_version_url = config["WEBDRIVER"]["latest_version_url"]

        logger.info('*** 00 updateWebDriver START ***')

        # --- WebDriver起動確認 ---
        error = check_webdriver_launch()

        # --- エラー内容に応じて更新処理を実行 ---
        if isinstance(error, (SessionNotCreatedException, FileNotFoundError, WebDriverException)):
            update_and_relaunch_webdriver(error, latest_version_url, webdriver_base_url)
        elif error is not True:
            logger.error(f"An unexpected error occurred: {error}")

    except Exception as e:
        logger.error(f'An unexpected error occurred in main process: {e}')
        sys.exit(1)
    finally:
        logger.info('*** 00 updateWebDriver END ***')

if __name__ == "__main__":
    main()
