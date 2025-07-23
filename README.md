# Recsav 連携自動化

このプロジェクトは、様々なオンラインサービス（例：楽天カード、Amazon）からの金融取引データをダウンロードし、Recsav へと連携するプロセスを自動化します。

## 機能

- **楽天カード明細ダウンロード**: 楽天 e-NAVI から CSV 明細をダウンロードします。
- **CSV を ifZaim へインポート**: ダウンロードした CSV データを`if_zaim`データベースにインポートします。
- **Recsav へのデータ連携**: 処理されたデータを`if_rakuten_card`から Recsav の`household_account_book`テーブルへ連携します。

## セットアップ

### 前提条件

- Python 3.x
- PostgreSQL (`if_zaim`および Recsav データベース用)
- Google Chrome ブラウザ
- ChromeDriver (お使いの Chrome ブラウザのバージョンと互換性のあるもの)

### インストール

1.  **リポジトリをクローンします:**
    ```bash
    git clone https://github.com/your-username/recsav_linking.git
    cd recsav_linking
    ```
2.  **Python の依存関係をインストールします:**
    ```bash
    pip install -r requirements.txt
    ```

### 設定

1.  **`settings.ini`**: プロジェクトのルートディレクトリに`settings.ini`ファイルを作成します。このファイルには、機密情報と設定の詳細が保存されます。

    ```ini
    [DB]
    host = あなたのDBホスト
    port = あなたのDBポート
    dbname = あなたのDB名
    user = あなたのDBユーザー
    password = あなたのDBパスワード

    [RAKUTEN]
    url = https://www.rakuten-card.co.jp/e-navi/
    user = あなたの楽天ID
    password = あなたの楽天パスワード
    csv_file_nm_prefix = rakuten_card

    [OUTPUT]
    dir = C:/Users/admin/Downloads/ # またはお好みのダウンロードディレクトリ

    [LOG]
    path = ./log/app.log

    [WEBDRIVER]
    chrome_driver = C:/path/to/your/chromedriver.exe # ChromeDriver実行可能ファイルへのパス
    ```

    **注意**: プレースホルダーの値を実際の認証情報とパスに置き換えてください。

2.  **ChromeDriver**: Google Chrome ブラウザに適切な ChromeDriver のバージョンを[ChromeDriver ダウンロード](https://chromedriver.chromium.org/downloads)からダウンロードし、`settings.ini`で指定されたパスに配置してください。

## 使い方

### 1. 楽天カード明細のダウンロード

```bash
python 10createRakutenCardCsv.py
```

このスクリプトは楽天 e-NAVI にログインし、設定された出力ディレクトリに CSV 明細をダウンロードします。

### 2. 楽天カード CSV をデータベースにインポート

```bash
python 11importCsvToIfRakutenCard.py
```

このスクリプトはダウンロードされた楽天カード CSV ファイルを読み込み、PostgreSQL データベースの`if_rakuten_card`テーブルにインポートします。

### 3. 楽天カードデータを Recsav に連携

```bash
python 12ifRakutenCardToRecsav.py
```

このスクリプトは`if_rakuten_card`のデータを処理し、Recsav データベースの`household_account_book`および`store`テーブルに挿入します。

## プロジェクト構造

- `00updateWebDriver.py`: WebDriver を更新するスクリプト（実装されている場合）。
- `10createRakutenCardCsv.py`: 楽天カード CSV をダウンロードします。
- `11importCsvToIfRakutenCard.py`: 楽天カード CSV を DB にインポートします。
- `12ifRakutenCardToRecsav.py`: 楽天カードデータを Recsav に連携します。
- `recsav_linking.bat`: 一連の連携スクリプト実行用のバッチファイル
- `requirements.txt`: Python の依存関係。
- `settings.ini`: 設定ファイル（ユーザー管理、Git にはコミットされません）。
- `log/`: ログファイル用のディレクトリ。
- `.gitignore`: Git で無視するファイル/ディレクトリを指定します。

## 注意事項

- **Web スクレイピングの安定性**: Web スクレイピングスクリプトは、対象ウェブサイトの HTML 構造に大きく依存します。楽天 e-NAVI ウェブサイトの変更により、スクリプトが動作しなくなる可能性があります。定期的なメンテナンスが必要になる場合があります。
- **エラーハンドリング**: 基本的なエラーハンドリングは実装されています。本番環境での使用には、より堅牢なエラーハンドリングとリトライメカニズムが必要になる場合があります。
- **セキュリティ**: `settings.ini`ファイルが適切に保護されていることを確認し、公開リポジトリに**絶対に**コミットしないでください。機密性の高い認証情報が含まれています。
