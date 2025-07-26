import os
import glob
import sys
import time
import traceback
from logzero import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import common


def create_driver(config):
    """
    設定に基づいてWebDriverを生成します。

    Args:
        config (configparser.ConfigParser): 設定オブジェクト

    Returns:
        webdriver.Chrome: 生成されたWebDriverインスタンス
    """
    chromedriver_path = config["WEBDRIVER"]["chrome_driver"]
    output_dir = config["OUTPUT"]["dir"]
    
    service = Service(executable_path=chromedriver_path)
    options = webdriver.ChromeOptions()
    # 必要なオプションを追加
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("prefs", {
        "download.default_directory": output_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    })
    
    return webdriver.Chrome(service=service, options=options)


def prepare_output_directory(output_dir, file_prefix):
    """
    出力ディレクトリを準備します。既存の対象CSVファイルは削除します。

    Args:
        output_dir (str): 出力ディレクトリのパス
        file_prefix (str): 削除対象のファイル接頭辞
    """
    logger.info('Preparing output directory.')
    os.makedirs(output_dir, exist_ok=True)
    
    # 既存のrakuten_card_*.csvファイルを削除
    for f in glob.glob(os.path.join(output_dir, f'{file_prefix}_*.csv')):
        os.remove(f)
        logger.info(f'Deleted existing file: {f}')


def login_to_rakuten(driver, wait, url, user, password):
    """
    楽天e-NAVIにログインします。

    Args:
        driver (webdriver.Chrome): WebDriverインスタンス
        wait (WebDriverWait): WebDriverWaitインスタンス
        url (str): ログインページのURL
        user (str): ユーザーID
        password (str): パスワード
    """
    logger.info('Logging in to Rakuten e-NAVI.')
    driver.get(url)

    # ユーザーID入力
    user_id_field = wait.until(EC.element_to_be_clickable((By.ID, "user_id")))
    user_id_field.clear()
    user_id_field.send_keys(user)
    wait.until(EC.element_to_be_clickable((By.ID, "cta001"))).click()

    # パスワード入力
    password_field = wait.until(EC.element_to_be_clickable((By.ID, "password_current")))
    password_field.clear()
    password_field.click()
    password_field.send_keys(password)
    password_field.send_keys(Keys.TAB)
    password_field.send_keys(Keys.TAB)
    password_field.send_keys(Keys.ENTER)

    # ログイン処理の完了を待つ
    time.sleep(5)
    logger.info('Login successful.')


def download_and_rename_csv(driver, wait, output_dir, file_prefix, tab_no):
    """
    指定されたタブの明細CSVをダウンロードし、リネームします。

    Args:
        driver (webdriver.Chrome): WebDriverインスタンス
        wait (WebDriverWait): WebDriverWaitインスタンス
        output_dir (str): 出力ディレクトリ
        file_prefix (str): ファイル名の接頭辞
        tab_no (int): ダウンロード対象のタブ番号
    """
    download_url = f"https://www.rakuten-card.co.jp/e-navi/members/statement/index.xhtml?tabNo={tab_no}"
    logger.info(f'Navigating to download page for tabNo={tab_no}')
    driver.get(download_url)
    
    # ダウンロード前のファイルリストを取得
    before_files = set(os.listdir(output_dir))

    # CSVダウンロードボタンをクリック
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".stmt-c-btn-dl.stmt-csv-btn"))).click()
    logger.info(f'CSV download initiated for tabNo={tab_no}')

    # ファイルのダウンロード完了を待機 (最大30秒)
    try:
        WebDriverWait(driver, 30).until(
            lambda d: any(f.startswith('enavi') and f.endswith('.csv') for f in os.listdir(output_dir) if f not in before_files)
        )
        after_files = set(os.listdir(output_dir))
        new_file_name = (after_files - before_files).pop()
        downloaded_path = os.path.join(output_dir, new_file_name)
        
        # ファイルをリネーム
        new_output_file = os.path.join(output_dir, f"{file_prefix}_tab{tab_no}.csv")
        os.rename(downloaded_path, new_output_file)
        logger.info(f'Successfully downloaded and renamed to: {new_output_file}')

    except Exception: # TimeoutExceptionだけでなく、他の例外も考慮
        logger.warning(f"Could not find downloaded CSV file for tabNo={tab_no}.")


def main():
    """
    メイン処理
    """
    driver = None
    try:
        # --- 初期設定 ---
        config = common.load_config()
        common.setup_logger(config["LOG"]["path"])
        
        rakuten_url = config["RAKUTEN"]["url"]
        rakuten_user = config["RAKUTEN"]["user"]
        rakuten_password = config["RAKUTEN"]["password"]
        csv_prefix = config["RAKUTEN"]["csv_file_nm_prefix"]
        output_dir = config["OUTPUT"]["dir"]

        logger.info('*** 10 createRakutenCardCsv START ***')

        # --- WebDriver生成とディレクトリ準備 ---
        driver = create_driver(config)
        wait = WebDriverWait(driver, 20)
        prepare_output_directory(output_dir, csv_prefix)

        # --- 楽天e-NAVIへログイン ---
        login_to_rakuten(driver, wait, rakuten_url, rakuten_user, rakuten_password)

        # --- 各タブの明細をダウンロード ---
        for tab_no in [0, 1, 2]:
            download_and_rename_csv(driver, wait, output_dir, csv_prefix, tab_no)

    except Exception as e:
        logger.error(f'An unexpected error occurred: {e}')
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        if driver:
            driver.quit()
        logger.info('*** 10 createRakutenCardCsv END ***')

if __name__ == "__main__":
    main()
