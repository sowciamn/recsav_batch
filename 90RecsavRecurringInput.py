import sys
import psycopg2
import traceback
import argparse
from logzero import logger
from datetime import datetime
import common


def get_execution_date():
    """
    コマンドライン引数から実行日を取得します。
    引数がない場合は、本日の日付を返します。

    Returns:
        datetime.date: 実行日
    """
    parser = argparse.ArgumentParser(description='定期的な支出を家計簿に登録します。')
    parser.add_argument(
        '--date', 
        type=str, 
        help='YYYY-MM-DD形式で実行日を指定します。例: --date 2023-01-01'
    )
    args = parser.parse_args()

    if args.date:
        try:
            return datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            logger.error("Invalid date format. Please use YYYY-MM-DD.")
            sys.exit(1)
    else:
        return datetime.today().date()


def delete_existing_recurring_data(cursor, exec_date):
    """
    指定された実行日の定期支出データを削除します。

    Args:
        cursor: データベースカーソル
        exec_date (datetime.date): 実行日
    """
    logger.info(f"Deleting existing recurring data for date: {exec_date}")
    sql = """
        DELETE FROM household_account_book
        WHERE actual_date = %s
          AND linking_data_type = 0
    """
    cursor.execute(sql, (exec_date,))
    logger.info(f"{cursor.rowcount} records deleted.")


def fetch_recurring_configs(cursor):
    """
    登録対象の定期支出設定を取得します。

    Args:
        cursor: データベースカーソル

    Returns:
        list: 定期支出設定のリスト
    """
    logger.info("Fetching recurring configurations.")
    sql = """
        SELECT
            category_cd, store_cd, amount, remarks, linking_data_type
        FROM
            recurring_config
        WHERE
            execution_interval_type = '1' -- 毎月実行
            AND active_flg = '1'
    """
    cursor.execute(sql)
    return cursor.fetchall()


def insert_recurring_data(cursor, exec_date, recurring_data):
    """
    取得した定期支出データを家計簿テーブルに登録します。

    Args:
        cursor: データベースカーソル
        exec_date (datetime.date): 実行日
        recurring_data (list): 登録するデータのリスト
    """
    logger.info(f"Registering {len(recurring_data)} recurring data entries.")
    insert_sql = """
        INSERT INTO household_account_book (
            actual_date, category_cd, store_cd, amount, remarks, linking_data_type
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    for record in recurring_data:
        cursor.execute(insert_sql, (exec_date,) + record)
    logger.info("All recurring data has been registered.")

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
        WHERE linking_data_type = 0
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
        
        logger.info('*** 90 RecsavRecurringInput START ***')

        # --- 実行日取得＆実行判定 ---
        execution_date = get_execution_date()
        if execution_date.day != 1:
            logger.info(f"Skipping process because it is not the first day of the month. Execution date: {execution_date}")
            return

        # --- DB接続 ---
        connection = common.get_db_connection(config)
        connection.autocommit = False
        cursor = connection.cursor()

        # --- データ処理 ---
        delete_existing_recurring_data(cursor, execution_date)
        recurring_configs = fetch_recurring_configs(cursor)

        if not recurring_configs:
            logger.info("No active recurring configurations found. Exiting.")
            return

        insert_recurring_data(cursor, execution_date, recurring_configs)

        update_linking_date(cursor)

        # --- コミット ---
        connection.commit()
        logger.info("Transaction committed successfully.")

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
        logger.info('*** 90 RecsavRecurringInput END ***')

if __name__ == "__main__":
    main()
