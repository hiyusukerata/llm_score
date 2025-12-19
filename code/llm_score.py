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

# 対応表の設定
TARGET_MAP = {
    "https://artificialanalysis.ai/providers/openai": "OpenAI",
    "https://artificialanalysis.ai/providers/google": "Google",
    "https://artificialanalysis.ai/providers/xai": "xAI",
    "https://artificialanalysis.ai/providers/anthropic": "Anthropic",
    "https://artificialanalysis.ai/providers/perplexity": "perplexity",
    "https://artificialanalysis.ai/providers/deepseek": "deepseek"
}

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

def write_to_sheet(sheet_name, data):
    try:
        creds = get_credentials()
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        if data:
            # 指定シートの2行目以降をクリア
            sheet.values().clear(
                spreadsheetId=SPREADSHEET_ID, 
                range=f"{sheet_name}!A2:Z1000"
            ).execute()
            
            # A2セルから書き込み
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{sheet_name}!A2",
                valueInputOption="RAW",
                body={"values": data}
            ).execute()
            print(f"✅ [{sheet_name}] シートの2行目から {len(data)} 行転記しました。")
        else:
            print(f"⚠️ [{sheet_name}] 転記するデータが見つかりませんでした。")
    except Exception as e:
         print(f"⚠️ [{sheet_name}] 書き込みエラー: {e}")

def init_webdriver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ja-JP")
    return webdriver.Chrome(options=options)

# ==========================
# スクレイピング関数
# ==========================
def scrape_provider_table(driver, url):
    rows_data = []
    try:
        print(f"🔍 取得中: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        
        # 親コンテナの待機
        parent_container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".container.m-auto.pb-8"))
        )

        # tbody を取得
        tbody = parent_container.find_element(By.TAG_NAME, "tbody")
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            
            row_content = [cell.text.strip().replace('\n', ' ') for cell in cells]
            if any(row_content):
                rows_data.append(row_content)
                
    except Exception as e:
        print(f"⚠️ スクレイピングエラー ({url}): {e}")
    
    return rows_data

# ==========================
# メインループ
# ==========================
if __name__ == "__main__":
    driver = init_webdriver()
    try:
        for url, sheet_name in TARGET_MAP.items():
            print(f"\n--- 処理開始: {sheet_name} ---")
            
            # データの抽出
            data = scrape_provider_table(driver, url)
            
            # スプレッドシートへの転記
            if data:
                write_to_sheet(sheet_name, data)
            
            # サーバー負荷軽減のための待機
            time.sleep(2)
            
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
    finally:
        driver.quit()
        print("\n✨ 全ての処理が完了しました。")
