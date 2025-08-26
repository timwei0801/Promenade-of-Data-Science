#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用多種方法處理有問題的SAV檔案
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
import logging

def setup_logging():
    """設定日誌記錄"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('alternative_sav_conversion.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def method_1_pyreadstat(sav_path):
    """方法1: 使用pyreadstat的不同參數"""
    import pyreadstat
    
    strategies = [
        {"name": "預設", "kwargs": {}},
        {"name": "無編碼", "kwargs": {"encoding": None}},
        {"name": "UTF-8", "kwargs": {"encoding": "utf-8"}},
        {"name": "BIG5", "kwargs": {"encoding": "big5"}},
        {"name": "GBK", "kwargs": {"encoding": "gbk"}},
        {"name": "CP950", "kwargs": {"encoding": "cp950"}},
        {"name": "Latin-1", "kwargs": {"encoding": "latin-1"}},
        {"name": "ISO-8859-1", "kwargs": {"encoding": "iso-8859-1"}},
    ]
    
    for strategy in strategies:
        try:
            print(f"  嘗試pyreadstat - {strategy['name']}")
            df, meta = pyreadstat.read_sav(sav_path, **strategy['kwargs'])
            print(f"  ✓ 成功! 維度: {df.shape}")
            return df, f"pyreadstat-{strategy['name']}"
        except Exception as e:
            print(f"  ✗ 失敗: {str(e)[:50]}...")
    
    return None, None

def method_2_savreaderwriter(sav_path):
    """方法2: 使用savReaderWriter（如果有安裝的話）"""
    try:
        from savReaderWriter import SavReader
        print("  嘗試savReaderWriter")
        
        with SavReader(sav_path) as reader:
            records = []
            for record in reader:
                records.append(record)
            
            # 獲取變數名稱
            var_names = reader.varNames
            
            # 創建DataFrame
            df = pd.DataFrame(records, columns=var_names)
            print(f"  ✓ 成功! 維度: {df.shape}")
            return df, "savReaderWriter"
            
    except ImportError:
        print("  ✗ savReaderWriter 未安裝")
        return None, None
    except Exception as e:
        print(f"  ✗ savReaderWriter 失敗: {str(e)[:50]}...")
        return None, None

def method_3_subprocess_pspp(sav_path, temp_csv_path):
    """方法3: 使用PSPP命令行工具（如果系統有安裝）"""
    import subprocess
    
    try:
        print("  嘗試PSPP轉換")
        
        # 創建PSPP腳本
        pspp_script = f"""
GET FILE='{sav_path}'.
SAVE TRANSLATE OUTFILE='{temp_csv_path}'
  /TYPE=CSV
  /ENCODING='UTF-8'
  /MAP
  /REPLACE
  /FIELDNAMES
  /CELLS=VALUES.
"""
        
        # 寫入暫存腳本檔案
        script_path = temp_csv_path.with_suffix('.sps')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(pspp_script)
        
        # 執行PSPP
        result = subprocess.run(['pspp', str(script_path)], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(temp_csv_path):
            df = pd.read_csv(temp_csv_path)
            # 清理暫存檔案
            os.remove(script_path)
            os.remove(temp_csv_path)
            print(f"  ✓ 成功! 維度: {df.shape}")
            return df, "PSPP"
        else:
            print(f"  ✗ PSPP 失敗: {result.stderr[:50] if result.stderr else 'unknown error'}")
            return None, None
            
    except subprocess.TimeoutExpired:
        print("  ✗ PSPP 超時")
        return None, None
    except FileNotFoundError:
        print("  ✗ PSPP 未安裝")
        return None, None
    except Exception as e:
        print(f"  ✗ PSPP 失敗: {str(e)[:50]}...")
        return None, None

def method_4_binary_inspection(sav_path):
    """方法4: 檢查檔案編碼和內容"""
    print("  檢查檔案編碼資訊")
    
    try:
        # 讀取檔案的前幾個bytes
        with open(sav_path, 'rb') as f:
            header = f.read(200)
        
        print(f"  檔案大小: {os.path.getsize(sav_path)} bytes")
        print(f"  檔案前32 bytes: {header[:32]}")
        
        # 檢查是否是有效的SAV檔案
        if header.startswith(b'$FL2'):
            print("  ✓ 確認是SAV格式檔案")
        else:
            print("  ✗ 可能不是標準SAV格式")
        
        # 嘗試偵測編碼
        try:
            import chardet
            with open(sav_path, 'rb') as f:
                raw_data = f.read(10000)  # 讀取前10KB
            encoding_result = chardet.detect(raw_data)
            print(f"  偵測編碼: {encoding_result}")
        except ImportError:
            print("  chardet 未安裝，無法偵測編碼")
        
    except Exception as e:
        print(f"  檔案檢查失敗: {e}")

def convert_problematic_sav(sav_path, csv_path):
    """嘗試多種方法轉換有問題的SAV檔案"""
    sav_path = Path(sav_path)
    csv_path = Path(csv_path)
    
    print(f"\n處理檔案: {sav_path.name}")
    print("=" * 50)
    
    # 檢查檔案是否存在
    if not sav_path.exists():
        print(f"✗ 檔案不存在: {sav_path}")
        return False
    
    # 檢查檔案編碼資訊
    method_4_binary_inspection(sav_path)
    
    # 嘗試不同的方法
    methods = [
        method_1_pyreadstat,
        method_2_savreaderwriter,
        lambda path: method_3_subprocess_pspp(path, csv_path.with_suffix('.temp.csv'))
    ]
    
    for i, method in enumerate(methods, 1):
        try:
            print(f"\n方法 {i}:")
            if i == 3:  # PSPP方法需要額外參數
                df, method_name = method(sav_path)
            else:
                df, method_name = method(sav_path)
            
            if df is not None:
                # 嘗試保存為CSV
                success = save_dataframe_as_csv(df, csv_path, method_name)
                if success:
                    print(f"🎉 成功轉換! 使用方法: {method_name}")
                    return True
                
        except Exception as e:
            print(f"  ✗ 方法 {i} 異常: {str(e)[:50]}...")
    
    print(f"\n❌ 所有方法都失敗，無法轉換: {sav_path.name}")
    return False

def save_dataframe_as_csv(df, csv_path, method_name):
    """嘗試多種編碼保存DataFrame為CSV"""
    encodings = ['utf-8-sig', 'utf-8', 'big5', 'gbk', 'latin-1']
    
    for encoding in encodings:
        try:
            # 預處理資料框，處理可能的編碼問題
            df_clean = df.copy()
            
            # 處理字串欄位
            for col in df_clean.select_dtypes(include=['object']).columns:
                try:
                    # 轉換為字串並清理
                    df_clean[col] = df_clean[col].astype(str)
                    # 替換問題字符
                    df_clean[col] = df_clean[col].str.replace('\x00', '', regex=False)  # 移除NULL字符
                    df_clean[col] = df_clean[col].str.replace('\ufeff', '', regex=False)  # 移除BOM
                except:
                    continue
            
            # 保存
            df_clean.to_csv(csv_path, index=False, encoding=encoding)
            print(f"  ✓ CSV保存成功 (編碼: {encoding})")
            return True
            
        except Exception as e:
            print(f"  ✗ 編碼 {encoding} 失敗: {str(e)[:30]}...")
    
    return False

def main():
    """主程式"""
    setup_logging()
    
    print("SAV檔案替代轉換工具")
    print("=" * 60)
    print("專門處理pyreadstat無法處理的SAV檔案")
    print()
    
    # 有問題的檔案列表
    problematic_files = [
        {
            "sav": "data/raw_data/D00175/data1.sav",
            "csv": "data/csv_output/D00175-1.csv"
        },
        {
            "sav": "data/raw_data/D00175/data2.sav",
            "csv": "data/csv_output/D00175-2.csv"
        }
    ]
    
    success_count = 0
    
    for file_info in problematic_files:
        if convert_problematic_sav(file_info["sav"], file_info["csv"]):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"轉換結果: {success_count}/{len(problematic_files)} 個檔案成功")
    
    if success_count == len(problematic_files):
        print("🎉 所有問題檔案都已成功轉換!")
    else:
        print("💡 建議:")
        print("1. 檢查原始SAV檔案是否損壞")
        print("2. 嘗試在SPSS中重新保存檔案")
        print("3. 安裝 savReaderWriter: pip install savReaderWriter")
        print("4. 安裝 PSPP (免費的SPSS替代品)")

if __name__ == "__main__":
    main()