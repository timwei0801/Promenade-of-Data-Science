import os
import pandas as pd
import pyreadstat
from pathlib import Path
import logging

def setup_logging():
    """設定日誌記錄"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('sav_to_csv_conversion.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def convert_sav_to_csv(sav_file_path, csv_file_path):
    """
    將單個SAV檔案轉換為CSV檔案，處理各種編碼問題
    
    Parameters:
    sav_file_path (str): SAV檔案的完整路徑
    csv_file_path (str): 要輸出的CSV檔案路徑
    
    Returns:
    bool: 轉換是否成功
    """
    # 嘗試不同的讀取方式來解決編碼問題
    read_strategies = [
        # 策略1：預設讀取方式
        lambda path: pyreadstat.read_sav(path),
        
        # 策略2：指定編碼為 None，讓 pyreadstat 自動偵測
        lambda path: pyreadstat.read_sav(path, encoding=None),
        
        # 策略3：指定常用的中文編碼
        lambda path: pyreadstat.read_sav(path, encoding='utf-8'),
        lambda path: pyreadstat.read_sav(path, encoding='big5'),
        lambda path: pyreadstat.read_sav(path, encoding='gbk'),
        lambda path: pyreadstat.read_sav(path, encoding='cp950'),
        
        # 策略4：忽略編碼錯誤
        lambda path: pyreadstat.read_sav(path, encoding='utf-8', encoding_errors='ignore'),
        lambda path: pyreadstat.read_sav(path, encoding='big5', encoding_errors='ignore'),
    ]
    
    df = None
    meta = None
    successful_strategy = None
    
    # 嘗試各種讀取策略
    for i, strategy in enumerate(read_strategies, 1):
        try:
            logging.info(f"嘗試讀取策略 {i}: {sav_file_path}")
            df, meta = strategy(sav_file_path)
            successful_strategy = i
            break
        except Exception as e:
            logging.warning(f"策略 {i} 失敗: {str(e)}")
            continue
    
    if df is None:
        logging.error(f"所有讀取策略都失敗，無法讀取: {sav_file_path}")
        return False
    
    try:
        # 嘗試不同的CSV寫入編碼
        csv_encodings = ['utf-8-sig', 'utf-8', 'big5', 'gbk']
        
        for encoding in csv_encodings:
            try:
                df.to_csv(csv_file_path, index=False, encoding=encoding)
                logging.info(f"成功轉換 (策略{successful_strategy}, 編碼{encoding}): {sav_file_path} -> {csv_file_path}")
                logging.info(f"資料維度: {df.shape[0]} rows × {df.shape[1]} columns")
                return True
            except Exception as e:
                logging.warning(f"CSV寫入編碼 {encoding} 失敗: {str(e)}")
                continue
        
        # 如果所有編碼都失敗，嘗試清理資料後再寫入
        logging.warning(f"嘗試清理資料後寫入: {sav_file_path}")
        
        # 清理字串欄位中的問題字符
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    df[col] = df[col].astype(str).str.encode('utf-8', errors='ignore').str.decode('utf-8')
                except:
                    # 如果還是失敗，就跳過這個欄位的處理
                    pass
        
        # 再次嘗試寫入
        df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
        logging.info(f"清理資料後成功轉換: {sav_file_path} -> {csv_file_path}")
        logging.info(f"資料維度: {df.shape[0]} rows × {df.shape[1]} columns")
        return True
        
    except Exception as e:
        logging.error(f"CSV寫入最終失敗 {sav_file_path}: {str(e)}")
        return False

def process_directory(source_dir, output_dir):
    """
    處理指定目錄下的所有SAV檔案
    
    Parameters:
    source_dir (str): 來源目錄路徑
    output_dir (str): 輸出目錄路徑
    """
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    
    # 確保輸出目錄存在
    output_path.mkdir(parents=True, exist_ok=True)
    
    total_converted = 0
    total_failed = 0
    
    # 遍歷所有子目錄
    for folder in source_path.iterdir():
        if folder.is_dir():
            folder_name = folder.name
            logging.info(f"處理資料夾: {folder_name}")
            
            # 找出該資料夾中的所有SAV檔案
            sav_files = list(folder.glob("*.sav"))
            
            if not sav_files:
                logging.info(f"資料夾 {folder_name} 中沒有找到SAV檔案")
                continue
            
            # 如果只有一個SAV檔案，直接使用資料夾名稱
            if len(sav_files) == 1:
                sav_file = sav_files[0]
                csv_filename = f"{folder_name}.csv"
                csv_path = output_path / csv_filename
                
                if convert_sav_to_csv(str(sav_file), str(csv_path)):
                    total_converted += 1
                else:
                    total_failed += 1
            
            # 如果有多個SAV檔案，使用編號命名
            else:
                for i, sav_file in enumerate(sav_files, 1):
                    csv_filename = f"{folder_name}-{i}.csv"
                    csv_path = output_path / csv_filename
                    
                    if convert_sav_to_csv(str(sav_file), str(csv_path)):
                        total_converted += 1
                    else:
                        total_failed += 1
    
    # 輸出轉換結果統計
    logging.info(f"轉換完成!")
    logging.info(f"成功轉換: {total_converted} 個檔案")
    logging.info(f"轉換失敗: {total_failed} 個檔案")

def main():
    """主函數"""
    # 設定日誌
    setup_logging()
    
    # 設定路徑 - 請根據你的實際路徑修改
    source_directory = "data/raw_data"  # 修改為你的SAV檔案所在目錄
    output_directory = "data/csv_output"  # 修改為你想要輸出CSV的目錄
    
    # 檢查來源目錄是否存在
    if not os.path.exists(source_directory):
        logging.error(f"來源目錄不存在: {source_directory}")
        print(f"錯誤: 找不到目錄 '{source_directory}'")
        print("請確認路徑是否正確，或修改 source_directory 變數")
        return
    
    logging.info(f"開始處理目錄: {source_directory}")
    logging.info(f"輸出目錄: {output_directory}")
    
    # 開始轉換
    process_directory(source_directory, output_directory)

if __name__ == "__main__":
    # 顯示使用說明
    print("SAV檔案轉CSV轉換器")
    print("=" * 50)
    print("此腳本會將指定目錄下所有子資料夾中的SAV檔案轉換為CSV檔案")
    print("轉換規則:")
    print("- 單個SAV檔案: 資料夾名稱.csv")
    print("- 多個SAV檔案: 資料夾名稱-1.csv, 資料夾名稱-2.csv, ...")
    print()
    
    # 詢問使用者是否要修改預設路徑
    user_input = input("是否使用預設路徑 'data/raw_data'? (y/n): ").lower().strip()
    
    if user_input == 'n':
        source_dir = input("請輸入SAV檔案所在目錄的路徑: ").strip()
        output_dir = input("請輸入CSV輸出目錄的路徑 (預設: data/csv_output): ").strip()
        
        if not output_dir:
            output_dir = "data/csv_output"
        
        # 設定日誌
        setup_logging()
        
        # 檢查來源目錄
        if not os.path.exists(source_dir):
            logging.error(f"來源目錄不存在: {source_dir}")
            print(f"錯誤: 找不到目錄 '{source_dir}'")
            import sys
            sys.exit(1)

        logging.info(f"開始處理目錄: {source_dir}")
        logging.info(f"輸出目錄: {output_dir}")
        
        # 開始轉換
        process_directory(source_dir, output_dir)
    else:
        main()