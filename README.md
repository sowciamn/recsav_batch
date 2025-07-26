# recsav-batch

家計簿アプリ `recsav` へのデータ連携を自動化するためのバッチ処理プロジェクトです。
楽天カードの利用明細を取得し、データベースへ自動で登録します。

## 主な機能

- **WebDriver の自動更新**: `00updateWebDriver.py` が実行環境の Chrome ブラウザに合わせた適切な WebDriver を自動でダウンロード・更新します。
- **楽天カード明細の自動取得**: `10createRakutenCardCsv.py` が Selenium を利用して楽天 e-NAVI にログインし、利用明細の CSV ファイルを自動でダウンロードします。
- **データベースへの自動連携**: `11` `12` のスクリプトが、ダウンロードした CSV を中間テーブルにインポートし、最終的に家計簿のメインテーブルへデータを整形・登録します。
- **定期的な支出の自動登録**: `90RecsavRecurringInput.py` が毎月 1 日に、設定ファイルに基づいた固定費（家賃、サブスクリプションなど）を自動で登録します。

## セットアップ

### 前提条件

- Python 3.x
- PostgreSQL
- Google Chrome ブラウザ

### インストール手順

1.  **リポジトリをクローンします:**

    ```bash
    git clone https://github.com/sowciamn/recsav_batch.git
    cd recsav_batch
    ```

2.  **Python の依存関係をインストールします:**
    ```bash
    pip install -r requirements.txt
    ```

### 設定 (`settings.ini`)

プロジェクトのルートディレクトリに `settings.ini` ファイルをコピーまたは新規作成し、ご自身の環境に合わせて内容を編集してください。

**注意:** このファイルには個人情報やパスワードが含まれるため、Git リポジトリなどで公開しないよう厳重に管理してください。

```ini
[DB]
host = localhost
port = 5432
dbname = your_db_name
dbuser = your_db_user
dbpassword = your_db_password

[RAKUTEN]
url = https://www.rakuten-card.co.jp/e-navi/
user = your_rakuten_id
password = your_rakuten_password
csv_file_nm_prefix = rakuten_card

[OUTPUT]
dir = C:/Users/your_user/Downloads/

[LOG]
path = ./log/app.log

[WEBDRIVER]
# このセクションは00updateWebDriver.pyによって自動管理されるため、
# 基本的に手動での設定は不要です。
chrome_driver = chromedriver.exe
webdriver_base_url = https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing
latest_version_url = https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json
```

## 実行方法

プロジェクトの全処理は、以下のバッチファイルを実行することで、正しい順序で実行されます。

```bash
recsav_batch.bat
```

## プロジェクト構成

- `recsav_batch.bat`: 全ての Python スクリプトを順番に実行するメインのバッチファイル。
- `common.py`: 設定ファイルの読み込み、ログ設定、DB 接続など、スクリプト間で共通の処理をまとめたモジュール。
- `00updateWebDriver.py`: `chromedriver.exe` を自動で最新版に更新します。
- `10createRakutenCardCsv.py`: 楽天 e-NAVI から利用明細 CSV をダウンロードします。
- `11importCsvToIfRakutenCard.py`: ダウンロードした CSV を中間 DB テーブル `if_rakuten_card` にインポートします。
- `12ifRakutenCardToRecsav.py`: 中間テーブルのデータを、マスタや家計簿テーブルに連携します。
- `90RecsavRecurringInput.py`: 毎月 1 日に定期的な支出を家計簿に登録します。
- `requirements.txt`: Python の依存パッケージリスト。
- `settings.ini`: データベース接続情報やログイン資格情報などを格納する設定ファイル（Git 管理外）。
- `log/`: ログファイルが格納されるディレクトリ。
- `.gitignore`: Git の追跡から除外するファイル（`settings.ini` や `log/` など）を指定。

## 注意事項

- **Web サイトの変更**: 楽天 e-NAVI のウェブサイトの HTML 構造が変更されると、スクレイピング処理が失敗する可能性があります。その場合は `10createRakutenCardCsv.py` の修正が必要になることがあります。
- **セキュリティ**: `settings.ini` ファイルには機密情報が含まれるため、取り扱いには十分注意してください。
