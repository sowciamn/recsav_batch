import sys
import configparser
import psycopg2
import traceback
import logging
import logzero
from logzero import logger
from datetime import datetime, date

### 引数取得 ###
args = sys.argv
arg_today = None
if len(args) > 1:
    arg_today = datetime.strptime(args[1] + ' 00:00:00', '%Y-%m-%d %H:%M:%S')

### 今日の日付設定 ###
# 引数がある場合はその日付を使用
# 引数がない場合は今日の日付を使用
today = datetime.today()
if arg_today is not None:
    today = arg_today

### 設定値取得 ###
config = configparser.ConfigParser()
config.read("settings.ini", "UTF-8")
host = config["DB"]["host"]
port = config["DB"]["port"]
dbname = config["DB"]["dbname"]
dbuser = config["DB"]["dbuser"]
dbpassword = config["DB"]["dbpassword"]
log_file = config["LOG"]["path"]

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

### DB接続設定 ###
context = "host={} port={} dbname={} user={} password={}"
context = context.format(host, port, dbname, dbuser, dbpassword)

### メイン処理 ###
con = None
try:
    logger.info('*** 90 RecsavRecurringInput START ***')

    # 実行日が1日でない場合は処理を終了
    if today.day != 1:
        logger.info(f"Skipping process because it is not the first day of the month. Execution date: {today.day}")
        sys.exit(0)

    with psycopg2.connect(context) as con:
        con.autocommit = False

        with con.cursor() as cur:
            # 家計簿テーブルに対象データが存在する場合は削除
            delete_sql = """
                DELETE FROM household_account_book
                WHERE actual_date = %s
                  AND linking_data_type = 0
            """
            cur.execute(delete_sql, (today,))
            logger.info(f"Deleted existing records for date: {today}")
            
            # 繰り返し設定テーブルから対象データを取得
            select_sql = """
                SELECT
                    category_cd,
                    store_cd,
                    amount,
                    remarks,
                    linking_data_type
                FROM
                    recurring_config
                WHERE
                    execution_interval_type = '1'
                    AND active_flg = '1'
            """
            cur.execute(select_sql)
            recurring_data = cur.fetchall()

            if not recurring_data:
                logger.info("No recurring data found.")
                sys.exit(0)

            logger.info(f"Registering {len(recurring_data)} recurring data entries.")

            # 家計簿テーブルへ登録
            insert_sql = """
                INSERT INTO household_account_book (
                    actual_date,
                    category_cd,
                    store_cd,
                    amount,
                    remarks,
                    linking_data_type
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """

            for record in recurring_data:
                category_cd, store_cd, amount, remarks, linking_data_type = record

                cur.execute(insert_sql, (
                    today,
                    category_cd,
                    store_cd,
                    amount,
                    remarks,
                    linking_data_type
                ))

except psycopg2.DatabaseError as e:
    if con:
        con.rollback()

    logger.error('Error: %s' % e)
    traceback.print_exc()
    sys.exit(1)

except Exception as e:
    if con:
        con.rollback()

    logger.error('Exception Error: %s' % e)
    traceback.print_exc()
    sys.exit(1)

finally:
    if con:
        con.commit()
        cur.close()
        con.close()
    logger.info('*** 90 RecsavRecurringInput END ***')