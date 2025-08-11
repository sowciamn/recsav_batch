import os
import sys
import csv
import psycopg2
import traceback
from logzero import logger
import common


def clear_if_rakuten_card_table(cursor):
    """
    if_rakuten_cardテーブルの全データを削除します。

    Args:
        cursor: データベースカーソル
    """
    logger.info("Clearing all data from if_rakuten_card table.")
    cursor.execute("DELETE FROM if_rakuten_card")


def insert_csv_data(cursor, csv_file_path, tab_no):
    """
    CSVファイルのデータをDBに挿入します。

    Args:
        cursor: データベースカーソル
        csv_file_path (str): CSVファイルのパス
        tab_no (int): CSVの種別を示すタブ番号
    """
    logger.info(f"Processing file: {csv_file_path}")
    
    sql = """
        INSERT INTO if_rakuten_card (
            usage_date, merchant_product_name, customer_nm, payment_method, 
            usage_amount, payment_fee, total_payment_amount, payment_month, 
            monthly_payment_amount, monthly_carryover_balance, new_signup_flag
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NULLIF(%s,''), %s, %s, NULLIF(%s, ''))
    """

    with open(csv_file_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)  # ヘッダー行をスキップ

        for row in reader:
            # 利用日が存在しない行はスキップ
            if not row or not row[0]:
                continue
            
            # tab_noに応じて挿入するデータを調整
            if tab_no == 0:
                params = (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], None, None, None)
            else:
                params = (row[0], row[1], row[2], row[3], row[4], row[5], row[6], None, row[7], row[8], row[9])
            
            cursor.execute(sql, params)
    logger.info(f"Finished processing file: {csv_file_path}")


def main():
    """
    メイン処理
    """
    connection = None
    try:
        # --- 初期設定 ---
        config = common.load_config()
        common.setup_logger(config["LOG"]["path"])
        csv_prefix = config["RAKUTEN"]["csv_file_nm_prefix"]
        output_dir = config["OUTPUT"]["dir"]

        logger.info('*** 11 importCsvToIfRakutenCard START ***')

        # --- DB接続 ---
        connection = common.get_db_connection(config)
        connection.autocommit = False
        cursor = connection.cursor()

        # --- テーブルクリア ---
        clear_if_rakuten_card_table(cursor)

        # --- CSVインポート ---
        for tab_no in [0, 1, 2]:
            csv_file_path = os.path.join(output_dir, f'{csv_prefix}_tab{tab_no}.csv')

            if not os.path.exists(csv_file_path):
                logger.warning(f'Input file does not exist, skipping: {csv_file_path}')
                continue
            
            insert_csv_data(cursor, csv_file_path, tab_no)

        # --- コミット ---
        connection.commit()
        logger.info("Data import committed successfully.")

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
        logger.info('*** 11 importCsvToIfRakutenCard END ***')

if __name__ == "__main__":
    main()
