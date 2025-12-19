#!/usr/bin/env python
# coding: utf-8

import os
import pickle
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# ==========================
# Google Sheets 設定
# ==========================
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
TOKEN_PICKLE_FILE = 'token.pickle'
# 指定されたスプレッドシートID
SPREADSHEET_ID = "12ub3XFQtIeBPU93dD3T4Nv4GaLT7TtnLoaFteEcYM4A"
TARGET_SHEET = "xAI"

# ==========================
# Google Sheets 認証
# ==========================
def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as f:
            creds = pickle.load(f)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("❌ 有効な token.pickle が必要です。ローカルで生成してリポジトリに含めるかSecretとして管理してください。")
    return creds

# ==========================
# Sheets 操作
# ==========================
def write_to_sheet(data):
    try:
        creds = get_credentials()
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        if data:
            # 既存の内容をクリア（A1からデータがある想定）
            sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range=f"{TARGET_SHEET}!A1:Z1000").execute()
            
            # データ書き込み
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{TARGET_SHEET}!A1",
                valueInputOption="RAW",
                body={"values": data}
            ).execute()
            print(f"✅ {len(data)} 行（ヘッダー含む）を {TARGET_SHEET} シートに転記しました。")
        else:
            print("⚠️ 転記するデータがありません。")
    except Exception as e:
         print(f"⚠️ 書き込み処理中にエラーが発生しました: {e}")

# ==========================
# Selenium WebDriver 初期化
# ==========================
def init_webdriver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # GitHub Actions上のChromeパス設定（必要に応じて）
    service = webdriver.chrome.service.Service()
    return webdriver.Chrome(service=service, options=options)

# ==========================
# クロール処理
# ==========================
def scrape_xai_table():
    url = "https://artificialanalysis.ai/providers/xai"
    driver = init_webdriver()
    all_rows = []
    
    print(f"🔍 ページにアクセス中: {url}")

    try:
        driver.get(url)
        # 指定されたクラスのコンテナが表示されるまで待機
        wait = WebDriverWait(driver, 20)
        container = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "container.m-auto.pb-8"))
        )
        
        # コンテナ内のテーブルを探す
        table = container.find_element(By.TAG_NAME, "table")
        
        # 1. ヘッダーの取得 (th)
        headers = []
        for th in table.find_elements(By.TAG_NAME, "th"):
            headers.append(th.text.strip())
        if headers:
            all_rows.append(headers)

        # 2. ボディ行の取得 (tr > td)
        rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            row_data = [cell.text.strip().replace('\n', ' ') for cell in cells]
            if any(row_data): # 空行でなければ追加
                all_rows.append(row_data)
                
    except Exception as e:
        print(f"⚠️ スクレイピング中にエラーが発生しました: {e}")
    finally:
        driver.quit()
    
    return all_rows

# ==========================
# メイン
# ==========================
if __name__ == "__main__":
    table_data = []
    try:
        # データの抽出
        table_data = scrape_xai_table()
        
        if table_data:
            print(f"--- 抽出プレビュー (先頭3行) ---")
            for row in table_data[:3]:
                print(row)
            
            # シートへ書き込み
            write_to_sheet(table_data)
        else:
            print("❌ データが取得できませんでした。")
            
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
