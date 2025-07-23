import sys
import configparser
import psycopg2
import traceback
import logging
import logzero
from logzero import logger
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

### 設定値取得 ###
config = configparser.ConfigParser()
config.read("settings.ini")
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

### if_rakuten → recsavテーブル連携 ###
try:
    logger.info('*** 12 ifRakutenCardToRecsav START ***')

    with psycopg2.connect(context) as con:
        con.autocommit = False

        with con.cursor() as cur:

            # iif_rakuten_cardのデータ件数を取得
            sql = ""
            sql = sql + "SELECT "
            sql = sql + "    COUNT(irc.*) AS CNT "
            sql = sql + "  , MIN(irc.usage_date) AS START_DATE "
            sql = sql + "  , MAX(irc.usage_date) AS END_DATE "
            sql = sql + "FROM if_rakuten_card irc "

            cur.execute(sql)
            row = cur.fetchone()

            # if_rakuten_cardにデータがある場合は後続処理を実行
            if row[0] > 0:
                start_date = row[1]
                end_date = row[2]
                logger.info('iif_rakuten_card 対象日：' + datetime.strftime(start_date,"%Y%m%d") + '～' + datetime.strftime(end_date, "%Y%m%d"))
                # household_account_bookテーブルのデータを削除する
                sql = "DELETE FROM household_account_book WHERE linking_data_type = 1 AND actual_date >= %s AND actual_date <= %s "
                cur.execute(sql, (datetime.strftime(
                    start_date, "%Y/%m/%d"), datetime.strftime(end_date, "%Y/%m/%d")))

                # if_rakuten_card → storeへデータ連携
                # 店登録されていないデータを登録
                sql = ""
                sql = sql + "INSERT INTO store( "
                sql = sql + "    store_nm "
                sql = sql + ") "
                sql = sql + "SELECT DISTINCT "
                sql = sql + "    irc.merchant_product_name "
                sql = sql + "FROM "
                sql = sql + "  if_rakuten_card irc "
                sql = sql + "WHERE 0=0 "
                sql = sql + "AND NOT EXISTS ( "
                sql = sql + "    SELECT "
                sql = sql + "        * "
                sql = sql + "    FROM "
                sql = sql + "      store s "
                sql = sql + "    WHERE "
                sql = sql + "      s.store_nm = irc.merchant_product_name "
                sql = sql + "  ) "
                cur.execute(sql)

                # if_rakuten_card → household_account_bookへデータ連携
                sql = ""
                sql = sql + "INSERT INTO household_account_book ( "
                sql = sql + "    actual_date "
                sql = sql + "  , category_cd "
                sql = sql + "  , store_cd "
                sql = sql + "  , amount "
                sql = sql + "  , remarks "
                sql = sql + "  , linking_data_type "
                sql = sql + ") "
                sql = sql + "WITH iv_category_mapping_config AS ( "
                sql = sql + " SELECT "
                sql = sql + "     irc.if_rakuten_card_seq "
                sql = sql + "   , irc.merchant_product_name "
                sql = sql + "   , cmc.category_cd "
                sql = sql + "   , cmc.linking_excluded_flg "
                sql = sql + " FROM category_mapping_config cmc "
                sql = sql + "  INNER JOIN if_rakuten_card irc "
                sql = sql + "     ON irc.merchant_product_name LIKE '%' || cmc.mapping_key_nm || '%' "
                sql = sql + ") "
                sql = sql + "SELECT "
                sql = sql + "    irc.usage_date AS actual_date "
                sql = sql + "  , CASE "
                sql = sql + "     WHEN icmc.category_cd IS NULL THEN 1000 "
                sql = sql + "	 ELSE icmc.category_cd "
                sql = sql + "    END AS category_cd "
                sql = sql + "  , s.store_cd "
                sql = sql + "  , irc.total_payment_amount AS amount "
                sql = sql + "  , NULL AS remarks "
                sql = sql + "  , 1 AS linking_data_type "
                sql = sql + "FROM if_rakuten_card irc "
                sql = sql + " LEFT OUTER JOIN iv_category_mapping_config icmc "
                sql = sql + "   ON icmc.if_rakuten_card_seq = irc.if_rakuten_card_seq "
                sql = sql + " LEFT OUTER JOIN store s "
                sql = sql + "   ON s.store_nm = irc.merchant_product_name "
                sql = sql + "WHERE icmc.linking_excluded_flg IS NULL "
                cur.execute(sql)

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
    logger.info('*** 12 ifRakutenCardToRecsav END ***')
