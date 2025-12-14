from flask import Flask, request, jsonify
import pandas as pd
import matplotlib
matplotlib.use('Agg') # 設定 Matplotlib 後端為非互動模式，用於伺服器環境
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io
from datetime import datetime
import numpy as np
import re

app = Flask(__name__)

# 設定圖表樣式
# 'Arial Unicode MS' 用於顯示中文
# 注意：在 Zeabur/Docker 環境中需要確保系統安裝了中文字體，否則可能無法正確顯示中文
sns.set_style("whitegrid")
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 核心消費分類規則
CATEGORIES = {
    '生活開銷': ['連加', '超商', 'UBER', '小北百貨', '築間', 'FOODPANDA', '呷尚寶', '珍煮丹', 'CoCo', '飲料', '星巴克', 'Subway', '麥當勞', '摩斯', '肯德基', '美食'],
    '軟體訂閱': ['GOOGL', 'Netflix', 'Spotify', 'Apple'],
    '交通費用': ['捷運', '公車', '台鐵', '高鐵', '加油'],
    '未分類': ['未分類']
}


def categorize_transaction(description):
    """根據交易描述 (摘要) 對交易進行分類"""
    description = str(description).upper()
    
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword.upper() in description:
                return category
    
    return '未分類'


def clean_currency(amount):
    """清理金額欄位，移除逗號和引號，並轉換為數字"""
    if pd.isna(amount):
        return 0
    # 移除千分位逗號和 CSV 中可能存在的引號，並轉換為 float
    return float(str(amount).replace(',', '').replace('"', '').strip())


@app.route('/api/analyze', methods=['POST'])
def analyze_data():
    """
    接收 POST 請求，處理 CSV 檔案，進行信用卡消費分析，並回傳結果與圖表。
    假設 n8n 傳遞的檔案參數名為 'csv_file'。
    """
    # 1. 檢查檔案上傳
    if 'csv_file' not in request.files:
        return jsonify({'error': '缺少檔案部分。請確保 Body Parameters 的 Name 設定為 csv_file。'}), 400

    file = request.files['csv_file']
    
    if file.filename == '':
        return jsonify({'error': '未選擇任何檔案'}), 400

    if file and file.filename.endswith('.csv'):
        try:
            # 2. 讀取檔案內容
            # 檔案有 3 行標頭資訊，所以從第 4 行 (header=3) 開始讀取資料
            csv_data = file.stream.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_data), header=3)
            
            # 3. 數據清理與準備 (修正欄位名稱以符合您的 CSV 檔案)
            # 您的 CSV 檔案提供的欄位是：'消費日', '摘要', '入帳起息日'
            required_cols = ['消費日', '摘要', '入帳起息日']  # <--- 修正處 1: 更改為 '入帳起息日'
            if not all(col in df.columns for col in required_cols):
                 return jsonify({'error': f'CSV 檔案缺少必要欄位：{required_cols}'}), 400

            # 轉換日期
            df['消費日'] = pd.to_datetime(df['消費日'], errors='coerce')
            
            # 處理金額欄位，移除逗號和引號
            # 使用您的 CSV 檔案中的 '入帳起息日' 欄位作為金額來源
            df['金額'] = df['入帳起息日'].apply(clean_currency) # <--- 修正處 2: 更改為 '入帳起息日'

            # 過濾掉金額為負數的項目 (通常是退款或扣繳，如「國泰銀扣繳」 )
            df = df[df['金額'] > 0]  
            
            # 4. 進行分類與分析
            df['分類'] = df['摘要'].apply(categorize_transaction)
            
            # 計算各分類的總支出
            spending_by_category = df.groupby('分類')['金額'].sum().sort_values(ascending=False)
            
            # 5. 生成圖表：長條圖 (Top Spending Categories)
            plt.figure(figsize=(10, 6))
            sns.barplot(x=spending_by_category.index, y=spending_by_category.values)
            plt.title('消費分類總支出 (Top Categories)')
            plt.xlabel('分類')
            plt.ylabel('金額 (元)')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # 6. 將圖表編碼為 Base64 字串
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            plt.close() # 關閉圖表以釋放記憶體
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            buffer.close()
            
            # 7. 返回 JSON 結果
            response_data = {
                'message': '分析成功！',
                'total_rows': len(df),
                'total_spending': round(spending_by_category.sum(), 2),
                'spending_summary': {k: round(v, 2) for k, v in spending_by_category.to_dict().items()},
                'chart_base64_png': img_base64
            }
            return jsonify(response_data), 200

        except Exception as e:
            # 捕獲並返回處理檔案時的錯誤
            return jsonify({'error': f'檔案處理失敗，請檢查欄位名稱和數據格式: {str(e)}'}), 500

    # 如果檔案類型不正確
    return jsonify({'error': '無效的檔案類型。只允許 CSV 檔案。'}), 400


# 這是 Flask 應用程式的啟動點
if __name__ == '__main__':
    # 這是本機測試用的，Gunicorn 在 Zeabur 上會使用 Dockerfile/Procfile 中的配置
    app.run(host='0.0.0.0', port=8000)