import sys
import psycopg2
import traceback
from logzero import logger
from datetime import datetime
import common


def get_target_period(cursor):
    """
    処理対象となる期間を取得します。

    Args:
        cursor: データベースカーソル

    Returns:
        tuple: (データ件数, 開始日, 終了日) or (0, None, None)
    """
    sql = """
        SELECT
            COUNT(*) AS CNT,
            MIN(usage_date) AS START_DATE,
            MAX(usage_date) AS END_DATE
        FROM if_rakuten_card
    """
    cursor.execute(sql)
    result = cursor.fetchone()
    return result if result else (0, None, None)

def insert_new_stores(cursor):
    """
    if_rakuten_cardに存在する新しい店舗名をstoreテーブルに登録します。

    Args:
        cursor: データベースカーソル
    """
    logger.info("Inserting new stores into the store table.")
    sql = """
        INSERT INTO store (store_nm)
        SELECT DISTINCT
            irc.merchant_product_name
        FROM
            if_rakuten_card irc
        WHERE NOT EXISTS (
            SELECT 1
            FROM store s
            WHERE s.store_nm = irc.merchant_product_name
        )
    """
    cursor.execute(sql)
    logger.info(f"{cursor.rowcount} new stores inserted.")


def insert_account_book_data(cursor):
    """
    if_rakuten_cardのデータから、household_account_bookテーブルに未登録のデータを登録します。

    Args:
        cursor: データベースカーソル
    """
    logger.info("Inserting data into household_account_book table.")
    sql = """
        INSERT INTO household_account_book (
            actual_date, category_cd, store_cd, amount, remarks, linking_data_type
        )
        WITH iv_category_mapping_config AS ( 
          SELECT
              irc.if_rakuten_card_seq
            , irc.merchant_product_name
            , cmc.category_cd
            , cmc.linking_excluded_flg 
          FROM
            category_mapping_config cmc 
            INNER JOIN if_rakuten_card irc 
              ON irc.merchant_product_name LIKE '%' || cmc.mapping_key_nm || '%'
        ) 
        SELECT
            irc.usage_date                   AS actual_date
          , coalesce(icmc.category_cd, 1000) AS category_cd
          , s.store_cd
          , irc.total_payment_amount         AS amount
          , NULL                             AS remarks
          , 1                                AS linking_data_type 
        FROM
          if_rakuten_card irc 
          LEFT OUTER JOIN iv_category_mapping_config icmc 
            ON icmc.if_rakuten_card_seq = irc.if_rakuten_card_seq 
          LEFT OUTER JOIN store s 
            ON s.store_nm = irc.merchant_product_name 
        WHERE
          icmc.linking_excluded_flg IS NULL 
          AND NOT EXISTS ( 
            SELECT
                * 
            FROM
              household_account_book hab 
            WHERE
              hab.actual_date = irc.usage_date 
              AND hab.store_cd = s.store_cd 
              AND hab.amount = irc.total_payment_amount 
              AND hab.linking_data_type = 1
          )
    """
    cursor.execute(sql)
    logger.info(f"{cursor.rowcount} records inserted into household_account_book.")


def update_linking_date(cursor):
    """
    linking_dataテーブルの最終連携日時を更新します。

    Args:
        cursor: データベースカーソル
    """
    logger.info("Updating last linking date.")
    sql = """
        UPDATE linking_data
        SET last_linking_date = CURRENT_DATE
        WHERE linking_data_type = 1
    """
    cursor.execute(sql)


def main():
    """
    メイン処理
    """
    connection = None
    try:
        # --- 初期設定 ---
        config = common.load_config()
        common.setup_logger(config["LOG"]["path"])

        logger.info('*** 12 ifRakutenCardToRecsav START ***')

        # --- DB接続 ---
        connection = common.get_db_connection(config)
        connection.autocommit = False
        cursor = connection.cursor()

        # --- 処理対象期間の取得 ---
        count, start_date, end_date = get_target_period(cursor)
        if count == 0:
            logger.info("No data to process in if_rakuten_card. Exiting.")
            return

        logger.info(f"Processing data for period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        # --- データ連携処理 ---
        insert_new_stores(cursor)
        insert_account_book_data(cursor)
        update_linking_date(cursor)

        # --- コミット ---
        connection.commit()
        logger.info("Data processing committed successfully.")

    except psycopg2.DatabaseError as e:
        logger.error(f'Database error occurred: {e}')
        logger.error(traceback.format_exc())
        if connection:
            connection.rollback()
            logger.info("Transaction rolled back.")
        sys.exit(1)
    except Exception as e:
        logger.error(f'An unexpected error occurred: {e}')
        logger.error(traceback.format_exc())
        if connection:
            connection.rollback()
            logger.info("Transaction rolled back.")
        sys.exit(1)
    finally:
        if connection:
            cursor.close()
            connection.close()
            logger.info("Database connection closed.")
        logger.info('*** 12 ifRakutenCardToRecsav END ***')

if __name__ == "__main__":
    main()
