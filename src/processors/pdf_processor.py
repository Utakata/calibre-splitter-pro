"""
PDF Processor - PDF処理エンジン (強化版)
PDF読み込み・章解析・分割処理 + エラーハンドリング強化
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

try:
    import PyPDF2
    import pdfplumber
except ImportError as e:
    logging.error(f"PDF処理ライブラリのインポートエラー: {e}")
    raise

from ..core.data_models import Document, Chapter, ChapterDetectionMethod, ProcessingStatus, SplitSettings, FileType, OutputFormat
from ..utils.exceptions import FileProcessingError, ChapterAnalysisError
from ..utils.constants import AppConstants, FileConstants
from ..utils.file_utils import sanitize_filename, get_safe_chapter_filename, ensure_unique_filename, validate_output_directory

class PDFProcessor:
    """PDF処理エンジン（エラーハンドリング強化版）"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chapter_patterns = FileConstants.CHAPTER_PATTERNS
    
    def read_pdf_document(self, file_path: str) -> Document:
        """PDFファイルを読み込みDocumentオブジェクトを作成"""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileProcessingError("ファイルが存在しません", file_path)
            
            # ファイル情報取得
            file_size = file_path_obj.stat().st_size
            
            # PDF読み込み・メタデータ抽出
            metadata = self._extract_pdf_metadata(file_path)
            
            # Documentオブジェクト作成
            document = Document(
                file_path=str(file_path_obj),
                file_name=file_path_obj.name,
                file_size=file_size,
                title=metadata.get('title', file_path_obj.stem),
                author=metadata.get('author', ''),
                metadata=metadata
            )
            
            self.logger.info(f"PDF文書読み込み完了: {document.title}")
            return document
            
        except Exception as e:
            error_msg = f"PDF読み込みエラー: {str(e)}"
            self.logger.error(error_msg)
            raise FileProcessingError(error_msg, file_path, str(e))
    
    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """PDFメタデータ抽出（安全性強化）"""
        metadata = {}
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # 基本情報
                metadata['page_count'] = len(pdf_reader.pages)
                
                # メタデータの安全な取得
                if hasattr(pdf_reader, 'metadata') and pdf_reader.metadata:
                    pdf_meta = pdf_reader.metadata
                    
                    metadata.update({
                        'title': self._safe_get_pdf_meta(pdf_meta, '/Title'),
                        'author': self._safe_get_pdf_meta(pdf_meta, '/Author'),
                        'subject': self._safe_get_pdf_meta(pdf_meta, '/Subject'),
                        'creator': self._safe_get_pdf_meta(pdf_meta, '/Creator'),
                        'producer': self._safe_get_pdf_meta(pdf_meta, '/Producer'),
                        'creation_date': self._safe_get_pdf_meta(pdf_meta, '/CreationDate'),
                        'modification_date': self._safe_get_pdf_meta(pdf_meta, '/ModDate'),
                    })
                
                # PDFバージョン
                try:
                    if hasattr(pdf_reader, 'pdf_header'):
                        metadata['pdf_version'] = pdf_reader.pdf_header
                    else:
                        metadata['pdf_version'] = 'unknown'
                except:
                    metadata['pdf_version'] = 'unknown'
                
                self.logger.debug(f"PDFメタデータ抽出完了: {metadata.get('title', 'unknown')}")
                
        except Exception as e:
            self.logger.warning(f"PDFメタデータ抽取エラー: {e}")
            metadata = {
                'title': Path(file_path).stem,
                'author': 'unknown',
                'page_count': 0
            }
        
        return metadata
    
    def _safe_get_pdf_meta(self, metadata, key: str) -> str:
        """PDFメタデータの安全な取得"""
        try:
            if metadata and key in metadata:
                value = metadata[key]
                if value:
                    return str(value).strip()
        except Exception as e:
            self.logger.debug(f"PDFメタデータ取得エラー ({key}): {e}")
        return ''
    
    def analyze_chapters(self, document: Document) -> List[Chapter]:
        """章構造解析（エラーハンドリング強化）"""
        try:
            chapters = []
            
            # アウトライン（ブックマーク）から章を抽出
            outline_chapters = self._extract_chapters_from_outline(document)
            
            if outline_chapters:
                chapters.extend(outline_chapters)
                self.logger.info(f"アウトラインから{len(outline_chapters)}章を検出")
            else:
                # アウトラインがない場合はテキストから推測
                text_chapters = self._extract_chapters_from_text(document)
                chapters.extend(text_chapters)
                self.logger.info(f"テキストから{len(text_chapters)}章を推測")
            
            # 章番号の正規化
            self._normalize_chapter_numbers(chapters)
            
            return chapters
            
        except Exception as e:
            error_msg = f"PDF章解析エラー: {str(e)}"
            self.logger.error(error_msg)
            raise ChapterAnalysisError(error_msg, document.file_path, str(e))
    
    def _extract_chapters_from_outline(self, document: Document) -> List[Chapter]:
        """アウトラインから章抽出（安全性強化）"""
        chapters = []
        
        try:
            with open(document.file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if not hasattr(pdf_reader, 'outline') or not pdf_reader.outline:
                    return chapters
                
                chapter_num = 1
                
                def process_outline_item(item, depth=0):
                    nonlocal chapter_num
                    
                    try:
                        if isinstance(item, list):
                            for subitem in item:
                                process_outline_item(subitem, depth + 1)
                        elif hasattr(item, 'title') and hasattr(item, 'page'):
                            # ブックマーク項目の処理
                            title = str(item.title).strip() if item.title else f"Chapter {chapter_num}"
                            page_num = self._safe_get_page_number(item.page, pdf_reader)
                            
                            if page_num > 0:
                                safe_title = sanitize_filename(title)
                                chapter = Chapter(
                                    document_id=document.id,
                                    chapter_number=chapter_num,
                                    title=safe_title,
                                    start_page=page_num,
                                    end_page=page_num,  # 後で調整
                                    detected_method=ChapterDetectionMethod.AUTO,
                                    confidence_score=0.9
                                )
                                chapters.append(chapter)
                                chapter_num += 1
                                
                    except Exception as e:
                        self.logger.warning(f"アウトライン項目処理エラー: {e}")
                
                # アウトラインを再帰的に処理
                process_outline_item(pdf_reader.outline)
                
                # 章の終了ページを設定
                self._set_chapter_end_pages(chapters, len(pdf_reader.pages))
                
        except Exception as e:
            self.logger.warning(f"アウトライン解析エラー: {e}")
        
        return chapters
    
    def _safe_get_page_number(self, page_ref, pdf_reader) -> int:
        """ページ番号の安全な取得"""
        try:
            if hasattr(page_ref, 'idnum'):
                # 間接参照の場合
                for page_num, page in enumerate(pdf_reader.pages):
                    if hasattr(page, 'idnum') and page.idnum == page_ref.idnum:
                        return page_num + 1
            elif isinstance(page_ref, int):
                return page_ref + 1
            elif hasattr(page_ref, 'page'):
                return int(page_ref.page) + 1
        except Exception as e:
            self.logger.debug(f"ページ番号取得エラー: {e}")
        return 0
    
    def _extract_chapters_from_text(self, document: Document) -> List[Chapter]:
        """テキストから章推測（安全性強化）"""
        chapters = []
        
        try:
            with pdfplumber.open(document.file_path) as pdf:
                chapter_num = 1
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text()
                        if not text:
                            continue
                        
                        # 章パターンをテキストから検索
                        for pattern in self.chapter_patterns:
                            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                            
                            for match in matches:
                                title = match.group().strip()
                                safe_title = sanitize_filename(title)
                                
                                chapter = Chapter(
                                    document_id=document.id,
                                    chapter_number=chapter_num,
                                    title=safe_title,
                                    start_page=page_num + 1,
                                    end_page=page_num + 1,  # 後で調整
                                    detected_method=ChapterDetectionMethod.AUTO,
                                    confidence_score=0.7
                                )
                                chapters.append(chapter)
                                chapter_num += 1
                                break  # 同じページでは1つだけ
                            
                            if chapters and chapters[-1].start_page == page_num + 1:
                                break  # 既に章が見つかった
                                
                    except Exception as e:
                        self.logger.warning(f"ページテキスト処理エラー (page={page_num}): {e}")
                        continue
                
                # 章の終了ページを設定
                self._set_chapter_end_pages(chapters, len(pdf.pages))
                
        except Exception as e:
            self.logger.warning(f"テキスト解析エラー: {e}")
        
        return chapters
    
    def _set_chapter_end_pages(self, chapters: List[Chapter], total_pages: int) -> None:
        """章の終了ページ設定"""
        for i, chapter in enumerate(chapters):
            if i < len(chapters) - 1:
                # 次の章の開始ページの前ページ
                chapter.end_page = chapters[i + 1].start_page - 1
            else:
                # 最後の章は文書の最終ページまで
                chapter.end_page = total_pages
            
            # 開始ページより終了ページが小さい場合の修正
            if chapter.end_page < chapter.start_page:
                chapter.end_page = chapter.start_page
    
    def _normalize_chapter_numbers(self, chapters: List[Chapter]) -> None:
        """章番号の正規化"""
        for idx, chapter in enumerate(chapters):
            chapter.chapter_number = idx + 1
    
    def split_pdf_by_chapters(self, document: Document, chapters: List[Chapter], 
                             settings: SplitSettings) -> List[str]:
        """PDF章別分割実行（エラーハンドリング強化）"""
        output_files = []
        
        try:
            # 出力ディレクトリ検証
            is_valid, error_msg = validate_output_directory(settings.output_directory)
            if not is_valid:
                raise FileProcessingError(f"出力ディレクトリエラー: {error_msg}")
            
            output_dir = Path(settings.output_directory)
            
            # 出力形式による処理分岐
            output_extension = settings.get_output_extension(document.file_type)
            requires_conversion = settings.requires_format_conversion(document.file_type)
            
            if requires_conversion and settings.output_format == OutputFormat.EPUB:
                # PDF → EPUB変換は将来実装
                self.logger.warning("PDF→EPUB変換は現在サポートされていません。PDF形式で出力します。")
                output_extension = ".pdf"
            
            with open(document.file_path, 'rb') as input_file:
                pdf_reader = PyPDF2.PdfReader(input_file)
                
                for chapter in chapters:
                    try:
                        if not chapter.is_valid_pdf_chapter:
                            self.logger.warning(f"無効な章をスキップ: {chapter.title}")
                            continue
                        
                        # 安全なファイル名生成
                        safe_filename = get_safe_chapter_filename(
                            document.title, 
                            chapter.chapter_number, 
                            chapter.title,
                            output_extension
                        )
                        
                        output_path = ensure_unique_filename(output_dir / safe_filename)
                        
                        # 章のページを抽出
                        pdf_writer = PyPDF2.PdfWriter()
                        
                        for page_num in range(chapter.start_page - 1, chapter.end_page):
                            try:
                                if 0 <= page_num < len(pdf_reader.pages):
                                    pdf_writer.add_page(pdf_reader.pages[page_num])
                            except Exception as e:
                                self.logger.warning(f"ページ追加エラー (page={page_num}): {e}")
                        
                        # メタデータ設定（preserve_metadataオプションを考慮）
                        if settings.preserve_metadata:
                            try:
                                pdf_writer.add_metadata({
                                    '/Title': chapter.title,
                                    '/Author': document.author,
                                    '/Subject': f"{document.title} - {chapter.title}",
                                    '/Creator': f"CalibreSplitter Pro v{AppConstants.VERSION}",
                                    '/Producer': f"CalibreSplitter Pro v{AppConstants.VERSION}",
                                })
                            except Exception as e:
                                self.logger.warning(f"メタデータ設定エラー: {e}")
                        
                        # ファイル出力
                        try:
                            with open(output_path, 'wb') as output_file:
                                pdf_writer.write(output_file)
                            
                            chapter.output_file_path = str(output_path)
                            chapter.split_status = ProcessingStatus.SUCCESS
                            output_files.append(str(output_path))
                            
                            self.logger.info(f"章分割完了: {chapter.title} -> {output_path.name}")
                            
                        except Exception as e:
                            self.logger.error(f"ファイル保存エラー ({chapter.title}): {e}")
                            chapter.split_status = ProcessingStatus.ERROR
                            
                    except Exception as e:
                        self.logger.warning(f"章処理エラー ({chapter.title}): {e}")
                        chapter.split_status = ProcessingStatus.ERROR
                        continue
        
        except Exception as e:
            error_msg = f"PDF分割処理エラー: {str(e)}"
            self.logger.error(error_msg)
            raise FileProcessingError(error_msg, document.file_path, str(e))
        
        return output_files
    
    def _generate_filename(self, document: Document, chapter: Chapter, 
                          naming_pattern: str) -> str:
        """ファイル名生成（後方互換性のため保持）"""
        try:
            # 新しい安全な方法にリダイレクト
            return get_safe_chapter_filename(
                document.title,
                chapter.chapter_number,
                chapter.title,
                ".pdf"
            ).replace(".pdf", "")  # 拡張子を除去
            
        except Exception as e:
            self.logger.error(f"ファイル名生成エラー: {e}")
            return f"chapter_{chapter.chapter_number:02d}"
