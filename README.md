# CalibreSplitter Pro

**PDF/EPUB章別分割GUIツール with 出力形式選択機能**

## 🚀 概要

CalibreSplitter Proは、PDF・EPUBファイルを章単位で自動分割するPythonベースのGUIアプリケーションです。直感的なユーザーインターフェースと強力な章検出アルゴリズムを提供し、大容量の電子書籍を効率的に管理できます。

## ✨ 主要機能

### 📖 ファイル処理
- **PDF/EPUBファイル対応** - 主要な電子書籍形式をサポート
- **章構造自動解析** - 目次・見出しから章境界を自動検出
- **メタデータ保持** - 原本の著者・タイトル情報を維持

### 🎨 出力形式選択（New!）
- **柔軟な出力形式** - 入力と同じ形式/PDF/EPUBから選択
- **将来の変換対応** - PDF↔EPUB変換機能の基礎実装
- **設定保存** - 出力設定を保存・復元

### 🖥️ ユーザーインターフェース
- **PyQt5 GUI** - クロスプラットフォーム対応
- **ドラッグ&ドロップ** - 直感的なファイル読み込み
- **リアルタイム進捗表示** - 処理状況の可視化
- **設定管理** - カスタマイズ可能な分割設定

### 📊 データ管理
- **SQLiteデータベース** - プロジェクト・設定の永続化
- **バッチ処理** - 複数ファイルの一括処理
- **エラーハンドリング** - 堅牢なエラー処理とログ

## 🛠️ 技術スタック

- **Python 3.8+** - メイン言語
- **PyQt5** - GUI フレームワーク
- **PyPDF2/pdfplumber** - PDF処理エンジン
- **ebooklib** - EPUB処理エンジン
- **SQLite** - データベース
- **Pathlib** - ファイルパス管理

## 📋 必要要件

```bash
# requirements.txt
PyQt5>=5.15.0
PyPDF2>=3.0.0
pdfplumber>=0.7.0
ebooklib>=0.18
sqlalchemy>=1.4.0
loguru>=0.6.0
```

## 🚀 インストール

### 1. リポジトリのクローン
```bash
git clone https://github.com/Utakata/calibre-splitter-pro.git
cd calibre-splitter-pro
```

### 2. 仮想環境の作成
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 依存関係インストール
```bash
pip install -r requirements.txt
```

### 4. アプリケーション起動
```bash
python main.py
```

## 💡 使用方法

### 基本的な使い方

1. **ファイル読み込み**
   - 「ファイルを開く」ボタンでPDF/EPUBを選択
   - ドラッグ&ドロップでも読み込み可能

2. **章解析実行**
   - 「章解析」ボタンで自動的に章構造を検出
   - 検出結果をプレビューで確認

3. **出力設定**
   - **出力フォルダ** を指定
   - **出力形式** を選択（同じ形式/PDF/EPUB）
   - **ファイル名パターン** をカスタマイズ

4. **分割実行**
   - 「分割実行」ボタンで処理開始
   - 進捗バーで処理状況を確認

### 高度な設定

- **章検出方法**: 自動/手動/XPath指定
- **命名パターン**: `{title}_{chapter_num}_{chapter_title}`
- **メタデータ保持**: 原本情報の継承
- **自動章番号**: 連番の自動付与

## 📁 プロジェクト構造

```
calibre-splitter-pro/
├── src/
│   ├── core/              # コアロジック
│   │   └── data_models.py # データモデル定義
│   ├── processors/        # ファイル処理エンジン
│   │   ├── pdf_processor.py
│   │   └── epub_processor.py
│   ├── ui/               # ユーザーインターフェース
│   │   └── main_window.py
│   ├── managers/         # データ・設定管理
│   │   ├── project_manager.py
│   │   ├── settings_manager.py
│   │   └── database_manager.py
│   └── utils/           # ユーティリティ
│       ├── constants.py
│       ├── exceptions.py
│       └── helpers.py
├── data/               # データファイル
│   ├── config/        # 設定ファイル
│   └── database/      # データベーススキーマ
├── main.py           # エントリーポイント
├── requirements.txt  # 依存関係
└── README.md        # このファイル
```

## 🆕 新機能: 出力形式選択

### OutputFormat列挙型
```python
class OutputFormat(Enum):
    SAME_AS_INPUT = "same"  # 入力ファイルと同じ形式
    PDF = "pdf"             # PDF形式
    EPUB = "epub"           # EPUB形式
```

### SplitSettings拡張
```python
@dataclass
class SplitSettings:
    output_format: OutputFormat = OutputFormat.SAME_AS_INPUT
    
    def get_output_extension(self, input_file_type: FileType) -> str:
        """出力ファイルの拡張子を取得"""
        
    def requires_format_conversion(self, input_file_type: FileType) -> bool:
        """形式変換が必要かどうかを判定"""
```

## 🔧 開発・貢献

### 開発環境セットアップ
```bash
# 開発用依存関係インストール
pip install -r requirements-dev.txt

# テスト実行
python -m pytest tests/

# コード品質チェック
flake8 src/
black src/
```

### 貢献ガイドライン
1. Issueで機能提案・バグ報告
2. フォーク・ブランチ作成
3. 変更実装・テスト追加
4. プルリクエスト作成

## 📄 ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照

## 🤖 開発支援

このプロジェクトは[Claude Code](https://claude.ai/code)の支援により開発されています。

## 📞 サポート

- **Issues**: バグ報告・機能要求
- **Discussions**: 質問・アイデア共有
- **Wiki**: 詳細ドキュメント

---

**CalibreSplitter Pro** - 効率的な電子書籍管理のための強力なツール 📚✨
