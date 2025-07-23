# RECSAV 連携

## 事前準備

- pip install -r requirements.txt

## createCsvForZaim

- Zaim からスクレイピングで直近 3 ヶ月の履歴データを抽出する
- WebApi はクレカのデータをひっぱれないのでスクレイピングにした
- 抽出対象のデータは先月と今月のデータ（クレカの時差があるので先月も対象にしている）
- 抽出したデータは zaim_rireki.csv として出力される
- 引数に日付を指定すると指定した日付から直近 3 ヶ月の履歴データを抽出する

## createBudgetsCsvForZaim

- Zaim からスクレイピングで実行年の予算データを抽出する

## importCsvToIfZaim

- RECSAV に if_zaim テーブル、if_zaim_budget テーブルを作成
- CSV データを if_zaim テーブル、if_zaim_budget テーブルへ連携する
- if_zaim テーブル、if_zaim_budget テーブルは洗い替え

## ifZaimToRecsav

- if_zaim テーブルのデータを RECSAV のテーブル（主に income,expense）へ連携する
- category は基本的に Zaim から手で連携する必要があるが、連携時にない場合は、自動で不明カテゴリの明細に作成する（カテゴリがないデータも連携漏れがないよう連携させるため）
- store はない場合は、自動で作成する
- if_zaim_budget テーブルのデータを RECSAV のテーブル（budget）へ連携する
