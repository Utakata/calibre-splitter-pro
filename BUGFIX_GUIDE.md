# エラー修正ガイド - CalibreSplitter Pro

## 🚨 修正されたエラー

### WinError 123: ファイル名構文エラー

**問題**: 
```
[WinError 123] ファイル名、ディレクトリ名、またはボリューム ラベルの構文が間違っています。: 
'55_エクササイズ③\n何を必要としているかを自覚する.epub'
```

**原因**: 
- 章タイトルに改行文字（`\n`）が含まれている
- Windowsファイルシステムで無効な文字が使用されている

**修正内容**: 
- `src/utils/file_utils.py` に包括的なファイル名サニタイズ機能を実装
- 無効文字の自動置換・除去
- Windows予約語対応
- ファイル名長制限

### EPUB コンテンツ抽出エラー

**問題**: 
```
EPUB コンテンツ抽出エラー: list index out of range
```

**原因**: 
- EPUBメタデータ取得時の配列範囲外アクセス
- 不完全なコンテンツ構造の処理不備

**修正内容**: 
- `src/processors/epub_processor.py` の全面的なエラーハンドリング強化
- 安全なメタデータ取得機能 (`_safe_get_metadata`)
- コンテンツ抽出の例外処理追加

## 🛠️ 実装された修正機能

### 1. ファイル名サニタイズ機能 (`src/utils/file_utils.py`)

```python
def sanitize_filename(filename: str, replacement: str = "_", max_length: int = 255) -> str:
    """ファイル名をサニタイズして安全な文字のみにする"""
    
def get_safe_chapter_filename(document_title: str, chapter_number: int, 
                            chapter_title: str, extension: str = ".epub") -> str:
    """章ファイル名の安全な生成"""
```

**対応する無効文字**:
- 改行文字: `\n`, `\r`, `\t`
- Windows無効文字: `<>:"/\\|?*`
- 制御文字・連続空白
- Windows予約語: `CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`

### 2. EPUB処理の安全性強化 (`src/processors/epub_processor.py`)

```python
def _safe_get_metadata(self, book, namespace: str, name: str) -> str:
    """メタデータの安全な取得"""
    
def _safe_get_item_content(self, item) -> Optional[str]:
    """アイテムコンテンツの安全な取得"""
```

**強化された機能**:
- 配列範囲外アクセス防止
- Unicode エンコーディング問題対応
- 不完全なEPUB構造への対応
- 各処理ステップでの例外処理

### 3. PDF処理の堅牢性向上 (`src/processors/pdf_processor.py`)

```python
def _safe_get_page_number(self, page_ref, pdf_reader) -> int:
    """ページ番号の安全な取得"""
    
def _safe_get_pdf_meta(self, metadata, key: str) -> str:
    """PDFメタデータの安全な取得"""
```

### 4. 出力ディレクトリ検証機能

```python
def validate_output_directory(directory: str) -> Tuple[bool, Optional[str]]:
    """出力ディレクトリの妥当性検証"""
```

**検証項目**:
- ディレクトリ存在確認
- 書き込み権限確認
- ディスク容量確認（簡易）
- ネットワークパス対応

### 5. ファイル重複回避機能

```python
def ensure_unique_filename(filepath: Path) -> Path:
    """ファイル名が重複する場合に連番を付与"""
```

## 🔄 修正前後の比較

### 修正前の問題ファイル名:
```
55_エクササイズ③
何を必要としているかを自覚する.epub
```

### 修正後の安全なファイル名:
```
55_エクササイズ③_何を必要としているかを自覚する.epub
```

## 📋 使用方法

### 1. 更新されたコードの取得

```bash
git clone https://github.com/Utakata/calibre-splitter-pro.git
cd calibre-splitter-pro
git pull origin main  # 最新の修正を取得
```

### 2. 依存関係の更新

```bash
pip install -r requirements.txt
```

### 3. アプリケーションの実行

```bash
python main.py
```

### 4. エラーが発生した場合

1. **ログの確認**: アプリケーションログでエラー詳細を確認
2. **出力先確認**: 出力ディレクトリの権限・容量を確認  
3. **ファイル名確認**: 問題のあるファイル名が自動修正されているか確認

## 🧪 テスト例

### ファイル名サニタイズのテスト

```python
from src.utils.file_utils import sanitize_filename

# テストケース
test_names = [
    "55_エクササイズ③\n何を必要としているかを自覚する",
    "Chapter<1>: Introduction?.epub",
    "CON.txt",  # Windows予約語
]

for name in test_names:
    safe_name = sanitize_filename(name)
    print(f"'{name}' → '{safe_name}'")
```

**期待される出力**:
```
'55_エクササイズ③\n何を必要としているかを自覚する' → '55_エクササイズ③_何を必要としているかを自覚する'
'Chapter<1>: Introduction?.epub' → 'Chapter_1___Introduction_.epub'
'CON.txt' → '_CON.txt'
```

## 🔍 トラブルシューティング

### Q: まだファイル名エラーが発生する

**A**: 
1. 最新のコードに更新されているか確認
2. `src/utils/file_utils.py` が正しくインポートされているか確認
3. ログでサニタイズ処理が実行されているか確認

### Q: EPUB処理でエラーが続く

**A**: 
1. EPUBファイルが破損していないか確認
2. 必要なライブラリ（ebooklib, lxml, beautifulsoup4）がインストールされているか確認
3. ログで具体的なエラー内容を確認

### Q: ネットワーク位置への出力でエラー

**A**: 
1. ネットワークドライブがマウントされているか確認
2. 書き込み権限があるか確認
3. ローカルディスクでテストしてから実行

## 📊 修正効果

### Before（修正前）:
- ❌ WinError 123 でファイル作成失敗
- ❌ list index out of range でEPUB処理中断
- ❌ 不安定な処理結果

### After（修正後）:
- ✅ 安全なファイル名自動生成
- ✅ 堅牢なEPUB/PDF処理
- ✅ 包括的なエラーハンドリング
- ✅ ネットワークパス対応

## 🎯 追加改善予定

1. **ログ出力の詳細化** - より詳しいデバッグ情報
2. **進捗表示の改善** - リアルタイム処理状況表示
3. **バッチ処理対応** - 複数ファイル一括処理の安定性向上
4. **設定の永続化** - ユーザー設定の保存・復元

---

**🔧 このガイドで解決しない問題がある場合**:
- GitHub Issues で報告してください: https://github.com/Utakata/calibre-splitter-pro/issues
- ログファイルと問題のファイル情報を含めてください
