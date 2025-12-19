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

def write_to_sheet(data):
    try:
        creds = get_credentials()
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        if data:
            # 2行目以降をクリア
            sheet.values().clear(
                spreadsheetId=SPREADSHEET_ID, 
                range=f"{TARGET_SHEET}!A2:Z1000"
            ).execute()
            
            # A2セルから書き込み
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{TARGET_SHEET}!A2",
                valueInputOption="RAW",
                body={"values": data}
            ).execute()
            print(f"✅ {len(data)} 行を {TARGET_SHEET} シートに転記しました。")
        else:
            print("⚠️ 転記するデータがありません。")
    except Exception as e:
         print(f"⚠️ 書き込み処理中にエラーが発生しました: {e}")

def init_webdriver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # GitHub Actionsでエラーが出やすい言語設定を固定
    options.add_argument("--lang=ja-JP")
    return webdriver.Chrome(options=options)

# ==========================
# クロール処理 (修正版)
# ==========================
def scrape_xai_models():
    url = "https://artificialanalysis.ai/providers/xai"
    driver = init_webdriver()
    rows_data = []
    
    try:
        print(f"🔍 ページにアクセス中: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        
        # 1. 確実に存在する親コンテナを待機
        # クラス名にスペースが含まれる場合は .class1.class2 の形式で指定
        parent_container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".container.m-auto.pb-8"))
        )
        print("✅ 親コンテナを確認しました。")

        # 2. 親コンテナの中にある tbody を取得
        # クラス名 [&_tr:last-child]:border-0 は特殊文字を含むため CSS セレクタを使わず、
        # 構造的に「container内の最初（または唯一）のtbody」を探すのが安全です
        tbody = parent_container.find_element(By.TAG_NAME, "tbody")
        
        # 3. tbody 内のすべての行 (tr) を取得
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        print(f"📊 {len(rows)} 個の行が見つかりました。解析を開始します。")
        
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
                
            # 文字列をクリーンアップしてリスト化
            row_content = [cell.text.strip().replace('\n', ' ') for cell in cells]
            if any(row_content):
                rows_data.append(row_content)
                
    except Exception as e:
        print(f"⚠️ スクレイピング中にエラーが発生しました: {e}")
    finally:
        driver.quit()
    
    return rows_data

if __name__ == "__main__":
    try:
        extracted_data = scrape_xai_models()
        if extracted_data:
            write_to_sheet(extracted_data)
        else:
            print("❌ データが取得できませんでした。サイトの構造が変更されたか、レンダリングが間に合っていない可能性があります。")
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
