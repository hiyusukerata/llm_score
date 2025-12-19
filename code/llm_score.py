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
STATUS_SHEET = "xAI"


# ==========================
# Google Sheets 認証 (省略)
# ==========================
def get_credentials():
    # ... 認証ロジックは元のまま ...
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
# Sheets 操作 (省略)
# ==========================

def write_to_sheet(data):
    # ... 書き込みロジックは元のまま ...
    try:
        creds = get_credentials()
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        if data:
            # 1行目は保持、2行目以降をクリア
            sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range=f"{STATUS_SHEET}!A2:C1000").execute()
            
            # データ書き込み
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{STATUS_SHEET}!A2:C",
                valueInputOption="RAW",
                body={"values": data}
            ).execute()
            print(f"✅ {len(data)} 行を {STATUS_SHEET} シートに転記しました。")
        else:
            print("⚠️ 転記するデータがありません。")
    except Exception as e:
         print(f"⚠️ 書き込み処理中にエラーが発生しました: {e}")

# ==========================
# Selenium WebDriver 初期化 (元のまま)
# ==========================
def init_webdriver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--incognito")
    options.add_argument("--lang=ja") # 日本語ロケール設定を維持
    service = webdriver.chrome.service.Service()
    return webdriver.Chrome(service=service, options=options)

# ==========================
# ページロード待ち（安定化）
# ==========================
def load_page(driver, url, timeout=15):
    driver.get(url)
    # daily-log要素が一つ以上描画されるまで待機
    WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "daily-log"))
    )
    time.sleep(1) 

# ==========================
# クロール処理（イベント抽出の厳密化）
# ==========================
def scrape_status(limit=5):
    url = "https://aistudio.google.com/status"
    driver = init_webdriver()
    all_rows = []
    
    print("\n========================================================")
    print(f"🔍 抽出対象の daily-log ({limit}件) のHTMLログ")
    print("========================================================")

    try:
        load_page(driver, url)
        
        container = driver.find_element(By.CLASS_NAME, "daily-log-container")
        daily_logs = container.find_elements(By.CLASS_NAME, "daily-log")
        
        # daily-logを上から5つに制限
        daily_logs = daily_logs[:limit]
        
        for i, daily_log in enumerate(daily_logs):
            # ログ出力（確認用）
            print(f"\n--- daily-log #{i+1} HTML ---")
            print(daily_log.get_attribute('outerHTML'))
            print("--------------------------------")

            # (1) タイトルを取得
            title = "Title Missing" 
            try:
                title_elems = daily_log.find_elements(By.CLASS_NAME, "incident-title")
                if title_elems:
                    title = title_elems[0].text.strip()
                else:
                    print(f"⚠️ daily-log #{i+1} でタイトル要素が見つかりませんでした。")
            except Exception as e:
                print(f"⚠️ daily-log #{i+1} インシデントタイトル取得失敗: {e}")
                
            # (2) イベントを取得
            # ★ 修正点: XPathで 'daily-log' (カレント要素) の直下の 'incident-event' のみを厳密に取得
            events = daily_log.find_elements(By.XPATH, "./div[@class='incident-event']")
            
            # イベントが直下に見つからなかった場合、子孫要素として広く探す（保険）
            if not events:
                 events = daily_log.find_elements(By.CLASS_NAME, "incident-event")
            
            for event in events:
                try:
                    status = event.find_element(By.CLASS_NAME, "incident-update-status").text.strip()
                    time_str = event.find_element(By.CLASS_NAME, "incident-update-time").text.strip()
                    
                    # 転記
                    all_rows.append([title, time_str, status])
                except Exception as e:
                    print(f"⚠️ daily-log #{i+1} イベント詳細（ステータス/時間）解析失敗: {e}")
            
    finally:
        driver.quit()
    
    return all_rows

# ==========================
# メイン (出力整形を伴う最終版)
# ==========================
if __name__ == "__main__":
    rows = []
    try:
        # バックアップとスクレイピングを実行
        rows = scrape_status(limit=5)
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")

    # 抽出結果を出力（タブ区切りで整形）
    print("\n--- 抽出結果 ---")
    
    # リストの要素をタブで結合して出力
    for row in rows:
        print('\t'.join(row))
    
    # シートへ書き込み
    write_to_sheet(rows)
