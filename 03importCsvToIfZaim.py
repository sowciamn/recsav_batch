import os
import sys
import configparser
import csv
import psycopg2
import traceback
import logging
import logzero
from logzero import logger

### 設定値取得 ###
config = configparser.ConfigParser()
config.read("settings.ini")
path = config["DB"]["path"]
port = config["DB"]["port"]
dbname = config["DB"]["dbname"]
dbuser = config["DB"]["dbuser"]
dbpassword = config["DB"]["dbpassword"]
history_csv = config["ZAIM"]["history_csv"]
budget_csv = config["ZAIM"]["budget_csv"]
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

### CSV設定 ###
csv_dir = os.path.dirname(os.path.abspath(__file__)) + "/output/"
history_csv_file_path = os.path.join(csv_dir, history_csv)
budget_csv_file_path = os.path.join(csv_dir, budget_csv)

### DB接続設定 ###
context = "host={} port={} dbname={} user={} password={}"
context = context.format(path, port, dbname, dbuser, dbpassword)

### CSV → if_zaimへデータ連携 ###
try:
    logger.info('*** 03 importCsvToIfZaim START ***')
    logger.info('読み込みファイル：' + history_csv_file_path + ' START')

    with psycopg2.connect(context) as con:
        con.autocommit = False

        with con.cursor() as cur:

            # if_zaimテーブルのデータを削除する
            sql = "DELETE FROM if_zaim "
            cur.execute(sql)

            # ファイルをオープンする
            with open(history_csv_file_path, mode="r", encoding="utf-8") as f:
                read = csv.reader(f)
                header = next(read)
                for row in read:
                    sql = "INSERT INTO "
                    sql = sql + "  if_zaim( "
                    sql = sql + "    if_zaim_date "
                    sql = sql + "  , if_zaim_method "
                    sql = sql + "  , if_zaim_category "
                    sql = sql + "  , if_zaim_category_detail "
                    sql = sql + "  , if_zaim_payment_source "
                    sql = sql + "  , if_zaim_deposit "
                    sql = sql + "  , if_zaim_item "
                    sql = sql + "  , if_zaim_remarks "
                    sql = sql + "  , if_zaim_store "
                    sql = sql + "  , if_zaim_currency "
                    sql = sql + "  , if_zaim_income_amount "
                    sql = sql + "  , if_zaim_expense_amount "
                    sql = sql + "  , if_zaim_transfer_amount "
                    sql = sql + "  , if_zaim_balance_amount "
                    sql = sql + "  , if_zaim_before_amount "
                    sql = sql + "  , if_zaim_aggregation_settings "
                    sql = sql + "  ) "
                    sql = sql + "VALUES "
                    sql = sql + "  ( "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s "
                    sql = sql + "  ) "

                    cur.execute(sql, (row[0], row[1], row[2], row[3], row[4],
                                      row[5], row[6], row[7], row[8], row[9],
                                      row[10], row[11], row[12], row[13], row[14],
                                      row[15]))

            logger.info('読み込みファイル：' + history_csv_file_path + ' END')

            logger.info('読み込みファイル：' + budget_csv_file_path + ' START')

            # if_zaim_budgetテーブルのデータを削除する
            sql = "DELETE FROM if_zaim_budget "
            cur.execute(sql)

            # ファイルをオープンする
            with open(budget_csv_file_path, mode="r", encoding="utf-8") as f:
                read = csv.reader(f)
                for row in read:
                    sql = "INSERT INTO "
                    sql = sql + "  if_zaim_budget( "
                    sql = sql + "    if_zaim_year_month "
                    sql = sql + "  , if_zaim_category "
                    sql = sql + "  , if_zaim_budget_amount "
                    sql = sql + "  ) "
                    sql = sql + "VALUES "
                    sql = sql + "  ( "
                    sql = sql + "    %s, "
                    sql = sql + "    %s, "
                    sql = sql + "    %s "
                    sql = sql + "  ) "

                    cur.execute(sql, (row[0], row[1], row[2]))

            logger.info('読み込みファイル：' + budget_csv_file_path + ' END')

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
    con.commit()
    if con:
        cur.close()
        con.close()
    logger.info('*** 03 importCsvToIfZaim END ***')
