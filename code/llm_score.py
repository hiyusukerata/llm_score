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
SPREADSHEET_ID = "12ub3XFQtIeBPU93dD3T4Nv4GaLT7TtnLoaFteEcYM4A"
TARGET_SHEET = "xAI"

# ==========================
# Google Sheets 認証
# ==========================
def get_credentials():
    if not os.path.exists(TOKEN_PICKLE_FILE):
        raise Exception("❌ token.pickle が存在しません。")
    with open(TOKEN_PICKLE_FILE, 'rb') as f:
        creds = pickle.load(f)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("❌ OAuth トークンが無効です。")
    return creds

# ==========================
# Sheets 操作 (2行目から転記)
# ==========================
def write_to_sheet(data):
    try:
        creds = get_credentials()
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        if data:
            # 1行目(見出し)を残し、2行目以降をクリア
            # A2:Z1000 の範囲をクリア
            sheet.values().clear(
                spreadsheetId=SPREADSHEET_ID, 
                range=f"{TARGET_SHEET}!A2:Z1000"
            ).execute()
            
            # データ書き込み (A2セルから開始)
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{TARGET_SHEET}!A2",
                valueInputOption="RAW",
                body={"values": data}
            ).execute()
            print(f"✅ {len(data)} 行のデータを {TARGET_SHEET} シートの2行目から転記しました。")
        else:
            print("⚠️ 転記するデータが見つかりませんでした。")
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
    service = webdriver.chrome.service.Service()
    return webdriver.Chrome(service=service, options=options)

# ==========================
# クロール処理 (ターゲットクラス指定)
# ==========================
def scrape_xai_models():
    url = "https://artificialanalysis.ai/providers/xai"
    driver = init_webdriver()
    rows_data = []
    
    try:
        print(f"🔍 ページにアクセス中: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        
        # 特殊なクラス名を持つ要素（テーブル本体やそのコンテナ）をCSSセレクタで特定
        # 特殊文字はエスケープが必要
        target_selector = ".[\\&_tr\\:last-child\\]\\:border-0"
        
        container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, target_selector))
        )
        
        # その要素内にあるすべての行(tr)を取得
        rows = container.find_elements(By.TAG_NAME, "tr")
        
        for row in rows:
            # 各行のセル(td)を取得
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue # ヘッダー行(th)などの場合はスキップ
                
            # テキストを抽出してリスト化
            row_content = [cell.text.strip().replace('\n', ' ') for cell in cells]
            if any(row_content): # 空でない行のみ追加
                rows_data.append(row_content)
                
    except Exception as e:
        print(f"⚠️ スクレイピング中にエラーが発生しました: {e}")
    finally:
        driver.quit()
    
    return rows_data

# ==========================
# メイン
# ==========================
if __name__ == "__main__":
    try:
        # 1. 指定されたクラスからデータを抽出
        extracted_data = scrape_xai_models()
        
        # 2. 抽出結果の確認とスプレッドシートへの書き込み
        if extracted_data:
            print(f"📊 抽出成功: {len(extracted_data)} 件のモデル情報を取得しました。")
            write_to_sheet(extracted_data)
        else:
            print("❌ 指定されたクラス内にデータが見つかりませんでした。")
            
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
