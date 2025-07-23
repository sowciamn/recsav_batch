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
host = config["DB"]["host"]
port = config["DB"]["port"]
dbname = config["DB"]["dbname"]
dbuser = config["DB"]["dbuser"]
dbpassword = config["DB"]["dbpassword"]
csv_file_nm_prefix = config["RAKUTEN"]["csv_file_nm_prefix"]
output_dir = config["OUTPUT"]["dir"]
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

### CSV → if_rakuten_cardへデータ連携 ###
try:
    logger.info('*** 11 importCsvToIfRakutenCard START ***')

    with psycopg2.connect(context) as con:
        con.autocommit = False
        with con.cursor() as cur:
            # if_rakuten_cardテーブルのデータを削除する
            sql = "DELETE FROM if_rakuten_card "
            cur.execute(sql)

            # 読み込みするtabNoのリスト
            tab_numbers = [0, 1, 2]

            # CSVファイルを読み込み、if_rakuten_cardテーブルにデータを挿入する
            for tab_no in tab_numbers:
                csv_file_path = output_dir + csv_file_nm_prefix + '_tab' + str(tab_no) + '.csv'

                # ファイルが存在しない場合はスキップ
                if not os.path.exists(csv_file_path):
                    logger.warning('Input file does not exist: ' + csv_file_path)
                    continue

                logger.info('Input file: ' + csv_file_path + ' START')

                # ファイルをオープンする
                with open(csv_file_path, mode="r", encoding="utf-8") as f:
                    read = csv.reader(f)
                    header = next(read)
                    for row in read:
                        # 利用日が空の場合はスキップ
                        if row[0] is None or row[0] == '':
                            continue
                        sql = ""
                        sql = sql + "INSERT INTO if_rakuten_card( "
                        sql = sql + "    usage_date "
                        sql = sql + "  , merchant_product_name "
                        sql = sql + "  , customer_nm "
                        sql = sql + "  , payment_method "
                        sql = sql + "  , usage_amount "
                        sql = sql + "  , payment_fee "
                        sql = sql + "  , total_payment_amount "
                        sql = sql + "  , payment_month "
                        sql = sql + "  , monthly_payment_amount "
                        sql = sql + "  , monthly_carryover_balance "
                        sql = sql + "  , new_signup_flag "
                        sql = sql + ") "
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
                        sql = sql + "    %s  "
                        sql = sql + "  ) "
                        if tab_no == 0:
                            cur.execute(sql, (row[0], row[1], row[2], row[3], row[4],
                                            row[5], row[6], row[7], row[8], row[9], row[10]))
                        else:
                            cur.execute(sql, (row[0], row[1], row[2], row[3], row[4],
                                            row[5], row[6], None, row[7], row[8], row[9]))

                logger.info('Input file: ' + csv_file_path + ' END')

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
    logger.info('*** 11 importCsvToIfRakutenCard END ***')
