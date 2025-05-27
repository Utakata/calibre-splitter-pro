"""
Data Models - データモデル定義
アプリケーションで使用するデータ構造の定義
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

class FileType(Enum):
    """ファイル種別"""
    PDF = "pdf"
    EPUB = "epub"
    UNKNOWN = "unknown"

class ChapterDetectionMethod(Enum):
    """章検出方法"""
    AUTO = "auto"           # 自動検出
    MANUAL = "manual"       # 手動設定
    XPATH = "xpath"         # XPath指定

class ProcessingStatus(Enum):
    """処理状態"""
    PENDING = "pending"     # 未処理
    RUNNING = "running"     # 処理中
    SUCCESS = "success"     # 成功
    ERROR = "error"         # エラー
    CANCELLED = "cancelled" # キャンセル

class OutputFormat(Enum):
    """出力形式"""
    SAME_AS_INPUT = "same"  # 入力ファイルと同じ形式
    PDF = "pdf"             # PDF形式
    EPUB = "epub"           # EPUB形式

@dataclass
class Project:
    """プロジェクトデータモデル"""
    id: Optional[int] = None
    name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    documents: List['Document'] = field(default_factory=list)
    
    def __post_init__(self):
        """初期化後処理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class Document:
    """文書データモデル"""
    id: Optional[int] = None
    project_id: Optional[int] = None
    file_path: str = ""
    file_name: str = ""
    file_type: FileType = FileType.UNKNOWN
    file_size: int = 0
    title: str = ""
    author: str = ""
    created_at: Optional[datetime] = None
    
    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 章情報
    chapters: List['Chapter'] = field(default_factory=list)
    
    # 処理状態
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    processing_message: str = ""
    
    def __post_init__(self):
        """初期化後処理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        
        # ファイルパスからファイル名を自動設定
        if self.file_path and not self.file_name:
            self.file_name = Path(self.file_path).name
        
        # ファイル拡張子からファイル種別を自動判定
        if self.file_path:
            ext = Path(self.file_path).suffix.lower()
            if ext == '.pdf':
                self.file_type = FileType.PDF
            elif ext == '.epub':
                self.file_type = FileType.EPUB
    
    @property
    def file_path_obj(self) -> Path:
        """ファイルパスをPathオブジェクトで取得"""
        return Path(self.file_path) if self.file_path else Path()
    
    @property
    def file_extension(self) -> str:
        """ファイル拡張子を取得"""
        return self.file_path_obj.suffix.lower()
    
    @property
    def is_pdf(self) -> bool:
        """PDFファイルかどうか"""
        return self.file_type == FileType.PDF
    
    @property
    def is_epub(self) -> bool:
        """EPUBファイルかどうか"""
        return self.file_type == FileType.EPUB
    
    @property
    def chapter_count(self) -> int:
        """章数を取得"""
        return len(self.chapters)
    
    @property
    def file_size_mb(self) -> float:
        """ファイルサイズをMBで取得"""
        return self.file_size / (1024 * 1024) if self.file_size > 0 else 0.0
    
    def add_chapter(self, chapter: 'Chapter') -> None:
        """章を追加"""
        chapter.document_id = self.id
        self.chapters.append(chapter)
    
    def get_chapter_by_number(self, chapter_number: int) -> Optional['Chapter']:
        """章番号で章を取得"""
        return next(
            (ch for ch in self.chapters if ch.chapter_number == chapter_number),
            None
        )

@dataclass
class Chapter:
    """章データモデル"""
    id: Optional[int] = None
    document_id: Optional[int] = None
    chapter_number: int = 0
    title: str = ""
    
    # PDF用属性
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    
    # EPUB用属性
    xpath: str = ""
    html_tag: str = ""
    html_content: str = ""
    
    # 検出情報
    detected_method: ChapterDetectionMethod = ChapterDetectionMethod.AUTO
    confidence_score: float = 0.0  # 検出確信度 (0.0-1.0)
    
    # 分割結果
    output_file_path: str = ""
    split_status: ProcessingStatus = ProcessingStatus.PENDING
    
    @property
    def page_count(self) -> int:
        """ページ数を取得（PDF用）"""
        if self.start_page is not None and self.end_page is not None:
            return self.end_page - self.start_page + 1
        return 0
    
    @property
    def page_range_str(self) -> str:  
        """ページ範囲を文字列で取得"""
        if self.start_page is not None and self.end_page is not None:
            if self.start_page == self.end_page:
                return f"p.{self.start_page}"
            return f"p.{self.start_page}-{self.end_page}"
        return ""
    
    @property
    def is_valid_pdf_chapter(self) -> bool:
        """有効なPDF章かどうか"""
        return (
            self.start_page is not None and 
            self.end_page is not None and 
            self.start_page <= self.end_page and
            self.start_page > 0
        )
    
    @property
    def is_valid_epub_chapter(self) -> bool:
        """有効なEPUB章かどうか"""
        return bool(self.xpath or self.html_tag)
    
    def __str__(self) -> str:
        """文字列表現"""
        if self.page_range_str:
            return f"第{self.chapter_number}章: {self.title} ({self.page_range_str})"
        return f"第{self.chapter_number}章: {self.title}"

@dataclass
class SplitSettings:
    """分割設定データモデル"""
    id: Optional[int] = None
    document_id: Optional[int] = None
    
    # 検出設定
    detection_method: ChapterDetectionMethod = ChapterDetectionMethod.AUTO
    target_heading_levels: List[str] = field(default_factory=lambda: ['h1', 'h2'])
    custom_xpath: str = ""
    
    # 出力設定
    output_directory: str = ""
    output_format: OutputFormat = OutputFormat.SAME_AS_INPUT  # 🆕 出力形式選択
    naming_pattern: str = "{title}_{chapter_num}_{chapter_title}"
    preserve_metadata: bool = True
    auto_number_chapters: bool = True
    
    # 処理設定
    overwrite_existing: bool = False
    create_subdirectories: bool = True
    
    @property
    def output_directory_path(self) -> Path:
        """出力ディレクトリをPathオブジェクトで取得"""
        return Path(self.output_directory) if self.output_directory else Path()
    
    def get_output_extension(self, input_file_type: FileType) -> str:
        """出力ファイルの拡張子を取得"""
        if self.output_format == OutputFormat.SAME_AS_INPUT:
            return ".pdf" if input_file_type == FileType.PDF else ".epub"
        elif self.output_format == OutputFormat.PDF:
            return ".pdf"
        elif self.output_format == OutputFormat.EPUB:
            return ".epub"
        return ".pdf"  # デフォルト
    
    def requires_format_conversion(self, input_file_type: FileType) -> bool:
        """形式変換が必要かどうかを判定"""
        if self.output_format == OutputFormat.SAME_AS_INPUT:
            return False
        elif self.output_format == OutputFormat.PDF:
            return input_file_type != FileType.PDF
        elif self.output_format == OutputFormat.EPUB:
            return input_file_type != FileType.EPUB
        return False
    
    def validate(self) -> List[str]:
        """設定の妥当性をチェック"""
        errors = []
        
        if not self.output_directory:
            errors.append("出力ディレクトリが指定されていません")
        elif not self.output_directory_path.exists():
            errors.append("出力ディレクトリが存在しません")
        
        if not self.naming_pattern:
            errors.append("ファイル命名パターンが指定されていません")
        
        if self.detection_method == ChapterDetectionMethod.XPATH and not self.custom_xpath:
            errors.append("XPath式が指定されていません")
        
        return errors

@dataclass  
class ProcessingResult:
    """処理結果データモデル"""
    document_id: Optional[int] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    message: str = ""
    
    # 処理統計
    total_chapters: int = 0
    processed_chapters: int = 0
    failed_chapters: int = 0
    
    # 処理時間
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # 出力ファイル情報
    output_files: List[str] = field(default_factory=list)
    
    # エラー情報
    error_details: List[str] = field(default_factory=list)
    
    @property
    def processing_time(self) -> Optional[float]:
        """処理時間を秒で取得"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """成功率を取得"""
        if self.total_chapters == 0:
            return 0.0
        return (self.processed_chapters / self.total_chapters) * 100
    
    @property
    def is_successful(self) -> bool:
        """処理が成功したかどうか"""
        return self.status == ProcessingStatus.SUCCESS and self.failed_chapters == 0
    
    def add_output_file(self, file_path: str) -> None:
        """出力ファイルを追加"""
        self.output_files.append(file_path)
        self.processed_chapters += 1
    
    def add_error(self, error_message: str) -> None:
        """エラーを追加"""
        self.error_details.append(error_message)
        self.failed_chapters += 1

@dataclass
class BatchProcessingConfig:
    """バッチ処理設定データモデル"""
    files: List[str] = field(default_factory=list)
    output_base_directory: str = ""
    parallel_processing: bool = True
    max_threads: int = 4
    continue_on_error: bool = True
    common_settings: Optional[SplitSettings] = None
    
    # 処理結果
    results: List[ProcessingResult] = field(default_factory=list)
    
    @property
    def file_count(self) -> int:
        """ファイル数を取得"""
        return len(self.files)
    
    @property
    def completed_count(self) -> int:
        """完了したファイル数を取得"""
        return len([r for r in self.results if r.status in [ProcessingStatus.SUCCESS, ProcessingStatus.ERROR]])
    
    @property
    def success_count(self) -> int:
        """成功したファイル数を取得"""
        return len([r for r in self.results if r.status == ProcessingStatus.SUCCESS])
    
    @property
    def error_count(self) -> int:
        """エラーファイル数を取得"""
        return len([r for r in self.results if r.status == ProcessingStatus.ERROR])
    
    @property
    def progress_percentage(self) -> float:
        """進捗パーセンテージを取得"""
        if self.file_count == 0:
            return 0.0
        return (self.completed_count / self.file_count) * 100

# 型エイリアス
DocumentList = List[Document]
ChapterList = List[Chapter]
ProcessingResultList = List[ProcessingResult]
