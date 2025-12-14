from flask import Flask, request, jsonify
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io
from datetime import datetime
import numpy as np
import re

app = Flask(__name__)

# 設定圖表樣式
sns.set_style("whitegrid")
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 核心消費分類規則 (來自你的 HTML)
CATEGORIES = {
    '生活開銷': ['連加', '超商', 'UBER', '小北百貨', '築間', 'FOODPANDA', '呷尚寶', '珍煮丹', 'CoCo', '飲料', '星巴克', 'Subway', '麥當勞', '摩斯', '肯德基', '美食'],
    '軟體訂閱': ['GOOGL'],  # <-- **已修正**：加上了閉合的 `]`
}