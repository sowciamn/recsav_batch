import configparser
import logging
import logzero
import psycopg2

# --- 定数 ---
SETTINGS_FILE = 'settings.ini'
LOG_FORMAT = '[%(levelname)s %(asctime)s] %(message)s'

def load_config():
    """
    設定ファイル (settings.ini) を読み込みます。

    Returns:
        configparser.ConfigParser: 読み込んだ設定オブジェクト
    """
    config = configparser.ConfigParser()
    config.read(SETTINGS_FILE, "utf-8")
    return config

def setup_logger(log_file):
    """
    ログ設定を初期化します。

    Args:
        log_file (str): ログファイルのパス
    """
    logzero.logfile(log_file,
                    maxBytes=10240,
                    backupCount=3,
                    loglevel=logging.INFO,
                    formatter=logging.Formatter(LOG_FORMAT))

def get_db_connection(config):
    """
    データベース接続を確立します。

    Args:
        config (configparser.ConfigParser): 設定オブジェクト

    Returns:
        psycopg2.connection: データベース接続オブジェクト
    """
    try:
        conn = psycopg2.connect(
            host=config["DB"]["host"],
            port=config["DB"]["port"],
            dbname=config["DB"]["dbname"],
            user=config["DB"]["dbuser"],
            password=config["DB"]["dbpassword"]
        )
        return conn
    except psycopg2.Error as e:
        # ログは呼び出し元で出すことを想定
        raise e
