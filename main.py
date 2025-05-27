#!/usr/bin/env python3
"""
CalibreSplitter Pro - Main Application Entry Point
PDF/EPUB章別分割ツール メインエントリーポイント

Usage:
    python main.py                    # GUI起動
    python main.py --cli              # CLI版起動  
    python main.py --help             # ヘルプ表示
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

# プロジェクトルートをPythonパスに追加
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.managers.log_manager import LogManager
from src.managers.settings_manager import SettingsManager  
from src.ui.main_window import MainWindow
from src.utils.constants import AppConstants
from src.utils.exceptions import CalibreSplitterError

def setup_logging() -> None:
    """ログシステムの初期化"""
    try:
        log_manager = LogManager()
        log_manager.setup_logging()
        logging.info("CalibreSplitter Pro が起動しました")
    except Exception as e:
        # ログ設定失敗時は標準出力に出力
        print(f"ログ設定エラー: {e}")

def setup_application() -> None:
    """アプリケーション初期設定"""
    try:
        # 設定ファイル初期化
        settings_manager = SettingsManager()
        settings_manager.initialize_settings()
        
        # データディレクトリ作成
        data_dir = PROJECT_ROOT / "data"
        for subdir in ["database", "config", "logs"]:
            (data_dir / subdir).mkdir(parents=True, exist_ok=True)
            
        logging.info("アプリケーション初期設定完了")
        
    except Exception as e:
        logging.error(f"アプリケーション初期設定エラー: {e}")
        raise CalibreSplitterError(f"初期設定に失敗しました: {e}")

def start_gui_application() -> int:
    """GUI版アプリケーション起動"""
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QIcon
        
        # Qt設定
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        app = QApplication(sys.argv)
        app.setApplicationName(AppConstants.APP_NAME)
        app.setApplicationVersion(AppConstants.VERSION)
        app.setOrganizationName(AppConstants.ORGANIZATION)
        
        # アプリケーションアイコン設定（存在する場合）
        icon_path = PROJECT_ROOT / "resources" / "icon.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        
        # メインウィンドウ作成・表示
        main_window = MainWindow()
        main_window.show()
        
        logging.info("GUIアプリケーションを開始")
        return app.exec_()
        
    except ImportError as e:
        error_msg = "PyQt5がインストールされていません。pip install PyQt5 を実行してください。"
        logging.error(error_msg)
        print(f"エラー: {error_msg}")
        return 1
        
    except Exception as e:
        error_msg = f"GUIアプリケーション起動エラー: {e}"
        logging.error(error_msg)
        print(f"エラー: {error_msg}")
        return 1

def start_cli_application() -> int:
    """CLI版アプリケーション起動（将来実装）"""
    print("CLI版は現在開発中です。")
    print("GUI版を起動するには: python main.py")
    return 0

def show_help() -> None:
    """ヘルプ表示"""
    help_text = f"""
CalibreSplitter Pro v{AppConstants.VERSION}
PDF/EPUB章別分割ツール

使用方法:
    python main.py              GUI版を起動
    python main.py --cli        CLI版を起動（開発中）
    python main.py --help       このヘルプを表示
    python main.py --version    バージョン情報を表示

機能:
    • PDF/EPUBファイルの章別自動分割
    • 章構造の自動検出・手動調整
    • XPath式による詳細な章検出設定
    • バッチ処理による複数ファイル一括処理
    • メタデータの保持・継承
    • 処理ログの管理・確認

詳細: https://github.com/calibre-splitter-pro/calibre-splitter-pro
"""
    print(help_text)

def show_version() -> None:
    """バージョン情報表示"""
    print(f"CalibreSplitter Pro v{AppConstants.VERSION}")
    print(f"Python {sys.version}")

def main() -> int:
    """メイン関数"""
    try:
        # コマンドライン引数処理
        args = sys.argv[1:] if len(sys.argv) > 1 else []
        
        if "--help" in args or "-h" in args:
            show_help()
            return 0
            
        if "--version" in args or "-v" in args:
            show_version()
            return 0
        
        # ログ・アプリケーション初期化
        setup_logging()
        setup_application()
        
        # アプリケーション起動
        if "--cli" in args:
            return start_cli_application()
        else:
            return start_gui_application()
            
    except KeyboardInterrupt:
        print("\nアプリケーションが中断されました。")
        return 130
        
    except CalibreSplitterError as e:
        logging.error(f"アプリケーションエラー: {e}")
        print(f"エラー: {e}")
        return 1
        
    except Exception as e:
        logging.error(f"予期しないエラー: {e}", exc_info=True)
        print(f"予期しないエラーが発生しました: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
