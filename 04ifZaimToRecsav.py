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
path = config["DB"]["path"]
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
context = context.format(path, port, dbname, dbuser, dbpassword)

### if_zaim → recsavテーブル連携 ###
try:
    logger.info('*** 04 ifZaimToRecsav START ***')

    with psycopg2.connect(context) as con:
        con.autocommit = False

        with con.cursor() as cur:

            # if_zaimのデータ件数を取得
            sql = ""
            sql = sql + "SELECT "
            sql = sql + "    COUNT(iz.*) AS CNT "
            sql = sql + \
                "  , DATE_TRUNC('month', MIN(iz.if_zaim_date)) AS START_DATE "
            sql = sql + \
                "  , DATE_TRUNC('month', MAX(iz.if_zaim_date)) + '1 month' +'-1 Day' AS END_DATE "
            sql = sql + "FROM if_zaim iz "

            cur.execute(sql)
            row = cur.fetchone()

            # if_zaimにデータがある場合は後続処理を実行
            if row[0] > 0:
                start_date = row[1]
                end_date = row[2]
                logger.info('if_zaim 対象月：' + datetime.strftime(start_date,
                                                               "%Y%m") + '～' + datetime.strftime(end_date, "%Y%m"))
                # incomeテーブルのデータを削除する
                sql = "DELETE FROM income WHERE income_date >= %s AND income_date <= %s "
                cur.execute(sql, (datetime.strftime(
                    start_date, "%Y/%m/%d"), datetime.strftime(end_date, "%Y/%m/%d")))

                # expenseテーブルのデータを削除する
                sql = "DELETE FROM expense WHERE expense_date >= %s AND expense_date <= %s "
                cur.execute(sql, (datetime.strftime(
                    start_date, "%Y/%m/%d"), datetime.strftime(end_date, "%Y/%m/%d")))

                # if_zaime → categoryへデータ連携
                # カテゴリ登録されていないカテゴリを登録
                sql = ""
                sql = sql + "INSERT INTO category ( "
                sql = sql + "    category_nm "
                sql = sql + "  , category_type "
                sql = sql + "  , display_order "
                sql = sql + ") "
                sql = sql + "SELECT DISTINCT "
                sql = sql + "    iz.if_zaim_category "
                sql = sql + "  , CASE "
                sql = sql + "     WHEN iz.if_zaim_method = 'income' THEN '1' "
                sql = sql + "     ELSE '2' "
                sql = sql + "    END "
                sql = sql + "  , 9999 "
                sql = sql + "FROM "
                sql = sql + "  if_zaim iz "
                sql = sql + "WHERE 0=0 "
                sql = sql + "AND iz.if_zaim_aggregation_settings = '常に集計に含める' "
                sql = sql + "AND iz.if_zaim_method IN('income','payment') "
                sql = sql + "AND NOT EXISTS ( "
                sql = sql + "    SELECT "
                sql = sql + "        * "
                sql = sql + "    FROM "
                sql = sql + "      category c "
                sql = sql + "    WHERE "
                sql = sql + "      c.category_nm = iz.if_zaim_category "
                sql = sql + "  ) "
                cur.execute(sql)

                # if_zaime → storeへデータ連携
                # 店登録されていないデータを登録
                sql = ""
                sql = sql + "INSERT INTO store( "
                sql = sql + "    store_nm "
                sql = sql + ") "
                sql = sql + "SELECT DISTINCT "
                sql = sql + "    iz.if_zaim_store "
                sql = sql + "FROM "
                sql = sql + "  if_zaim iz "
                sql = sql + "WHERE 0=0 "
                sql = sql + "AND iz.if_zaim_aggregation_settings = '常に集計に含める' "
                sql = sql + "AND iz.if_zaim_method IN('income','payment') "
                sql = sql + "AND NOT EXISTS ( "
                sql = sql + "    SELECT "
                sql = sql + "        * "
                sql = sql + "    FROM "
                sql = sql + "      store s "
                sql = sql + "    WHERE "
                sql = sql + "      s.store_nm = iz.if_zaim_store "
                sql = sql + "  ) "
                sql = sql + "AND iz.if_zaim_store <> '-' "
                cur.execute(sql)

                # if_zaime → incomeへデータ連携
                sql = ""
                sql = sql + "INSERT INTO income( "
                sql = sql + "    income_date "
                sql = sql + "  , category_cd "
                sql = sql + "  , store_cd "
                sql = sql + "  , income_amount "
                sql = sql + "  , income_remarks "
                sql = sql + ") "
                sql = sql + "SELECT "
                sql = sql + "    iz.if_zaim_date "
                sql = sql + "  , c.category_cd "
                sql = sql + "  , s.store_cd "
                sql = sql + "  , SUM(iz.if_zaim_income_amount) "
                sql = sql + "  , iz.if_zaim_category_detail || '　' || iz.if_zaim_remarks "
                sql = sql + "FROM "
                sql = sql + "  if_zaim iz "
                sql = sql + "  INNER JOIN category c "
                sql = sql + "    ON c.category_nm = iz.if_zaim_category "
                sql = sql + "    AND c.category_type = '1' "
                sql = sql + "  LEFT OUTER JOIN store s "
                sql = sql + "    ON s.store_nm = iz.if_zaim_store "
                sql = sql + "WHERE 0=0 "
                sql = sql + "AND iz.if_zaim_aggregation_settings = '常に集計に含める' "
                sql = sql + "AND iz.if_zaim_method = 'income' "
                sql = sql + "GROUP BY "
                sql = sql + "    iz.if_zaim_date "
                sql = sql + "  , c.category_cd "
                sql = sql + "  , s.store_cd "
                sql = sql + "  , iz.if_zaim_category_detail || '　' || iz.if_zaim_remarks "
                cur.execute(sql)

                # if_zaime → expenseへデータ連携
                sql = ""
                sql = sql + "INSERT INTO expense( "
                sql = sql + "    expense_date "
                sql = sql + "  , category_cd "
                sql = sql + "  , store_cd "
                sql = sql + "  , expense_amount "
                sql = sql + "  , expense_remarks "
                sql = sql + ") "
                sql = sql + "SELECT "
                sql = sql + "    iz.if_zaim_date "
                sql = sql + "  , c.category_cd "
                sql = sql + "  , s.store_cd "
                sql = sql + "  , SUM(iz.if_zaim_expense_amount) "
                sql = sql + "  , iz.if_zaim_category_detail || '　' || iz.if_zaim_remarks "
                sql = sql + "FROM "
                sql = sql + "  if_zaim iz "
                sql = sql + "  INNER JOIN category c "
                sql = sql + "    ON c.category_nm = iz.if_zaim_category "
                sql = sql + "    AND c.category_type = '2' "
                sql = sql + "  LEFT OUTER JOIN store s "
                sql = sql + "    ON s.store_nm = iz.if_zaim_store "
                sql = sql + "WHERE 0=0 "
                sql = sql + "AND iz.if_zaim_aggregation_settings = '常に集計に含める' "
                sql = sql + "AND iz.if_zaim_method = 'payment' "
                sql = sql + "GROUP BY "
                sql = sql + "    iz.if_zaim_date "
                sql = sql + "  , c.category_cd "
                sql = sql + "  , s.store_cd "
                sql = sql + "  , iz.if_zaim_category_detail || '　' || iz.if_zaim_remarks "
                cur.execute(sql)

            # if_zaim_budgetのデータ件数を取得
            sql = ""
            sql = sql + "SELECT "
            sql = sql + "    COUNT(iz.*) AS CNT "
            sql = sql + \
                "  , DATE_TRUNC('month', MIN(iz.if_zaim_year_month)) AS START_DATE "
            sql = sql + \
                "  , DATE_TRUNC('month', MAX(iz.if_zaim_year_month)) AS END_DATE "
            sql = sql + "FROM if_zaim_budget iz "

            cur.execute(sql)
            row = cur.fetchone()

            # if_zaim_budgetにデータがある場合は後続処理を実行
            if row[0] > 0:
                start_date = row[1]
                end_date = row[2]
                logger.info('if_zaim_budget 対象月：' + datetime.strftime(start_date,
                                                                      "%Y%m") + '～' + datetime.strftime(end_date, "%Y%m"))
                # budgetテーブルのデータを削除する
                sql = "DELETE FROM budget WHERE budget_year_month >= %s AND budget_year_month <= %s "
                cur.execute(sql, (datetime.strftime(
                    start_date, "%Y/%m/%d"), datetime.strftime(end_date, "%Y/%m/%d")))

                # if_zaime_budget → budgetへデータ連携
                sql = ""
                sql = sql + "INSERT INTO budget( "
                sql = sql + "    budget_year_month "
                sql = sql + "  , category_cd "
                sql = sql + "  , budget_amount "
                sql = sql + "  , budget_remarks "
                sql = sql + ") "
                sql = sql + "SELECT "
                sql = sql + "    izb.if_zaim_year_month "
                sql = sql + "  , c.category_cd "
                sql = sql + "  , izb.if_zaim_budget_amount "
                sql = sql + "  , NULL "
                sql = sql + "FROM if_zaim_budget izb "
                sql = sql + " INNER JOIN category c "
                sql = sql + "   ON c.category_nm = izb.if_zaim_category "
                sql = sql + "WHERE 0=0 "
                sql = sql + "ORDER BY "
                sql = sql + "    izb.if_zaim_year_month "
                sql = sql + "  , c.display_order "
                cur.execute(sql)

                # income → budgetへデータ連携(収入の実績金額分＝予算とする)
                sql = ""
                sql = sql + "INSERT INTO budget( "
                sql = sql + "    budget_year_month "
                sql = sql + "  , category_cd "
                sql = sql + "  , budget_amount "
                sql = sql + "  , budget_remarks "
                sql = sql + ") "
                sql = sql + "SELECT "
                sql = sql + "    TO_DATE(TO_CHAR(DATE_TRUNC('month',i.income_date), 'YYYY/MM/DD'), 'YYYY/MM/DD') AS if_zaim_year_month "
                sql = sql + "  , i.category_cd "
                sql = sql + "  , i.income_amount AS if_zaim_budget_amount "
                sql = sql + "  , i.income_remarks "
                sql = sql + "FROM income i "
                sql = sql + " LEFT OUTER JOIN budget b "
                sql = sql + "   ON TO_CHAR(b.budget_year_month, 'YYYY/MM/DD') = TO_CHAR(DATE_TRUNC('month',i.income_date), 'YYYY/MM/DD') "
                sql = sql + "  AND b.category_cd = i.category_cd "
                sql = sql + "WHERE 0=0 "
                sql = sql + "AND b.budget_seq IS NULL "
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
    logger.info('*** 04 ifZaimToRecsav END ***')
