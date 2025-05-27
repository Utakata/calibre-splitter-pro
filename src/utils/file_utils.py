"""
File Utilities - ファイル操作ユーティリティ
ファイル名サニタイズ、パス操作、ファイル検証など
"""

import os
import re
import unicodedata
from pathlib import Path
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Windowsで無効なファイル名文字
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\n\r\t]'

# 予約語（Windows）
RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

def sanitize_filename(filename: str, replacement: str = "_", max_length: int = 255) -> str:
    """
    ファイル名をサニタイズして安全な文字のみにする
    
    Args:
        filename: 元のファイル名
        replacement: 無効文字の置換文字
        max_length: 最大ファイル名長
    
    Returns:
        サニタイズされたファイル名
    """
    if not filename:
        return "untitled"
    
    try:
        # Unicode正規化
        filename = unicodedata.normalize('NFKC', str(filename))
        
        # 改行文字と制御文字を除去
        filename = re.sub(r'[\n\r\t\f\v]', ' ', filename)
        
        # 連続する空白を単一の空白に
        filename = re.sub(r'\s+', ' ', filename)
        
        # 先頭・末尾の空白とピリオドを除去
        filename = filename.strip(' .')
        
        # 無効な文字を置換
        filename = re.sub(INVALID_FILENAME_CHARS, replacement, filename)
        
        # 連続する置換文字を単一に
        if replacement:
            pattern = re.escape(replacement) + r'+'
            filename = re.sub(pattern, replacement, filename)
        
        # 先頭・末尾の置換文字を除去
        filename = filename.strip(replacement + ' ')
        
        # 予約語チェック
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in RESERVED_NAMES:
            filename = f"{replacement}{filename}"
        
        # 長すぎる場合は短縮
        if len(filename) > max_length:
            name = Path(filename).stem
            ext = Path(filename).suffix
            max_name_length = max_length - len(ext) - 10  # バッファ
            
            if max_name_length > 0:
                filename = f"{name[:max_name_length]}...{ext}"
            else:
                filename = f"truncated{ext}"
        
        # 空の場合のフォールバック
        if not filename or filename == replacement:
            filename = "untitled"
            
        logger.debug(f"ファイル名サニタイズ: '{filename}' → '{filename}'")
        return filename
        
    except Exception as e:
        logger.error(f"ファイル名サニタイズエラー: {e}")
        return "error_filename"

def safe_join_path(*parts) -> Path:
    """
    安全なパス結合（パストラバーサル攻撃対策）
    
    Args:
        *parts: パス要素
    
    Returns:
        安全に結合されたPath
    """
    try:
        # 各パート要素をサニタイズ
        safe_parts = []
        for part in parts:
            if not part:
                continue
                
            # 危険な文字列除去
            part = str(part).replace('..', '').replace('~', '')
            part = re.sub(r'[<>:"|?*]', '_', part)
            
            if part and part not in ['.', '..']:
                safe_parts.append(part)
        
        if not safe_parts:
            return Path('.')
            
        return Path(*safe_parts)
        
    except Exception as e:
        logger.error(f"パス結合エラー: {e}")
        return Path('safe_path')

def ensure_unique_filename(filepath: Path) -> Path:
    """
    ファイル名が重複する場合に連番を付与
    
    Args:
        filepath: 元のファイルパス
    
    Returns:
        ユニークなファイルパス
    """
    if not filepath.exists():
        return filepath
    
    counter = 1
    original_stem = filepath.stem
    suffix = filepath.suffix
    parent = filepath.parent
    
    while True:
        new_name = f"{original_stem} ({counter}){suffix}"
        new_path = parent / new_name
        
        if not new_path.exists():
            return new_path
            
        counter += 1
        
        # 無限ループ防止
        if counter > 9999:
            import time
            timestamp = int(time.time())
            new_name = f"{original_stem}_{timestamp}{suffix}"
            return parent / new_name

def validate_output_directory(directory: str) -> Tuple[bool, Optional[str]]:
    """
    出力ディレクトリの妥当性検証
    
    Args:
        directory: 検証対象ディレクトリ
    
    Returns:
        (妥当性, エラーメッセージ)
    """
    try:
        if not directory:
            return False, "出力ディレクトリが指定されていません"
        
        path = Path(directory)
        
        # パスの存在確認
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return False, f"ディレクトリを作成できません: {e}"
        
        # 書き込み権限確認
        if not os.access(path, os.W_OK):
            return False, "書き込み権限がありません"
        
        # ディスク容量確認（簡易）
        try:
            stat = os.statvfs(path) if hasattr(os, 'statvfs') else None
            if stat and stat.f_bavail < 1024 * 1024:  # 1MB未満
                return False, "ディスク容量が不足している可能性があります"
        except:
            pass  # Windows等では無視
        
        return True, None
        
    except Exception as e:
        return False, f"ディレクトリ検証エラー: {e}"

def get_safe_chapter_filename(document_title: str, chapter_number: int, 
                            chapter_title: str, extension: str = ".epub") -> str:
    """
    章ファイル名の安全な生成
    
    Args:
        document_title: 文書タイトル
        chapter_number: 章番号
        chapter_title: 章タイトル
        extension: ファイル拡張子
    
    Returns:
        安全なファイル名
    """
    try:
        # 基本的なテンプレート
        if chapter_title and chapter_title.strip():
            # 章タイトルをサニタイズ
            safe_title = sanitize_filename(chapter_title)
            filename = f"{chapter_number:02d}_{safe_title}"
        else:
            # 章タイトルがない場合
            safe_doc_title = sanitize_filename(document_title)
            filename = f"{safe_doc_title}_第{chapter_number:02d}章"
        
        # 拡張子を追加
        if not filename.lower().endswith(extension.lower()):
            filename += extension
        
        # 最終的な長さ制限
        if len(filename) > 200:  # 安全マージン
            name_part = filename[:-len(extension)]
            filename = f"{name_part[:190]}...{extension}"
        
        return filename
        
    except Exception as e:
        logger.error(f"章ファイル名生成エラー: {e}")
        return f"chapter_{chapter_number:02d}{extension}"

def is_network_path(path: str) -> bool:
    """
    ネットワークパスかどうか判定
    
    Args:
        path: 判定対象パス
    
    Returns:
        ネットワークパスの場合True
    """
    try:
        path_str = str(path)
        return (
            path_str.startswith(r'\\') or  # Windows UNC path
            path_str.startswith('//') or   # Unix network path
            ':' in path_str and not (len(path_str) > 1 and path_str[1] == ':')  # 非ローカルドライブ
        )
    except:
        return False

def normalize_path_separators(path: str) -> str:
    """
    パス区切り文字の正規化
    
    Args:
        path: 正規化対象パス
    
    Returns:
        正規化されたパス
    """
    try:
        # OSに応じた区切り文字に統一
        return str(Path(path))
    except:
        return path

# テスト用の例
if __name__ == "__main__":
    # サニタイズテスト例
    test_names = [
        "55_エクササイズ③\n何を必要としているかを自覚する",
        "Chapter 1: Introduction",
        "Test<>File|Name?.txt",
        "   Spaces and \t tabs \n\r newlines   ",
        "CON.txt",  # 予約語
        "a" * 300,  # 長すぎるファイル名
    ]
    
    for name in test_names:
        safe_name = sanitize_filename(name)
        print(f"'{name}' → '{safe_name}'")
