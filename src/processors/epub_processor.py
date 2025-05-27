"""
EPUB Processor - EPUB処理エンジン (強化版)
EPUB読み込み・章解析・分割処理 + エラーハンドリング強化
"""

import logging
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import html

try:
    import ebooklib
    from ebooklib import epub
    from lxml import etree, html as lxml_html
    import bs4
    from bs4 import BeautifulSoup
except ImportError as e:
    logging.error(f"EPUB処理ライブラリのインポートエラー: {e}")
    raise

from ..core.data_models import Document, Chapter, ChapterDetectionMethod, ProcessingStatus, SplitSettings, FileType, OutputFormat
from ..utils.exceptions import FileProcessingError, ChapterAnalysisError
from ..utils.constants import AppConstants, FileConstants
from ..utils.file_utils import sanitize_filename, get_safe_chapter_filename, ensure_unique_filename, validate_output_directory

class EPUBProcessor:
    """EPUB処理エンジン（エラーハンドリング強化版）"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chapter_patterns = FileConstants.CHAPTER_PATTERNS
    
    def read_epub_document(self, file_path: str) -> Document:
        """EPUBファイルを読み込みDocumentオブジェクトを作成"""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileProcessingError("ファイルが存在しません", file_path)
            
            # ファイル情報取得
            file_size = file_path_obj.stat().st_size
            
            # EPUB読み込み・メタデータ抽出
            metadata = self._extract_epub_metadata(file_path)
            
            # Documentオブジェクト作成
            document = Document(
                file_path=str(file_path_obj),
                file_name=file_path_obj.name,
                file_size=file_size,
                title=metadata.get('title', file_path_obj.stem),
                author=metadata.get('author', ''),
                metadata=metadata
            )
            
            self.logger.info(f"EPUB文書読み込み完了: {document.title}")
            return document
            
        except Exception as e:
            error_msg = f"EPUB読み込みエラー: {str(e)}"
            self.logger.error(error_msg)
            raise FileProcessingError(error_msg, file_path, str(e))
    
    def _extract_epub_metadata(self, file_path: str) -> Dict[str, Any]:
        """EPUBメタデータ抽出（安全性強化）"""
        metadata = {}
        
        try:
            book = epub.read_epub(file_path)
            
            # 基本メタデータの安全な取得
            metadata.update({
                'title': self._safe_get_metadata(book, 'DC', 'title'),
                'author': self._safe_get_metadata(book, 'DC', 'creator'),
                'language': self._safe_get_metadata(book, 'DC', 'language'),
                'publisher': self._safe_get_metadata(book, 'DC', 'publisher'),
                'date': self._safe_get_metadata(book, 'DC', 'date'),
                'description': self._safe_get_metadata(book, 'DC', 'description'),
                'identifier': self._safe_get_metadata(book, 'DC', 'identifier'),
            })
            
            # EPUBバージョン
            try:
                metadata['epub_version'] = book.version if hasattr(book, 'version') else 'unknown'
            except:
                metadata['epub_version'] = 'unknown'
            
            # ページ数（概算）
            try:
                items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
                metadata['estimated_pages'] = len(items)
            except:
                metadata['estimated_pages'] = 0
            
            self.logger.debug(f"メタデータ抽出完了: {metadata.get('title', 'unknown')}")
            
        except Exception as e:
            self.logger.warning(f"メタデータ抽出エラー: {e}")
            metadata = {
                'title': Path(file_path).stem,
                'author': 'unknown',
                'language': 'unknown'
            }
        
        return metadata
    
    def _safe_get_metadata(self, book, namespace: str, name: str) -> str:
        """メタデータの安全な取得"""
        try:
            values = book.get_metadata(namespace, name)
            if values and len(values) > 0:
                # タプルの場合は最初の要素を取得
                value = values[0]
                if isinstance(value, (tuple, list)) and len(value) > 0:
                    return str(value[0]).strip()
                return str(value).strip()
        except Exception as e:
            self.logger.debug(f"メタデータ取得エラー ({namespace}:{name}): {e}")
        return ''
    
    def analyze_chapters(self, document: Document) -> List[Chapter]:
        """章構造解析（エラーハンドリング強化）"""
        try:
            chapters = []
            
            # EPUBファイル読み込み
            book = epub.read_epub(document.file_path)
            
            # 目次から章を抽出
            toc_chapters = self._extract_chapters_from_toc(book, document)
            
            if toc_chapters:
                chapters.extend(toc_chapters)
                self.logger.info(f"目次から{len(toc_chapters)}章を検出")
            else:
                # 目次がない場合はコンテンツから推測
                content_chapters = self._extract_chapters_from_content(book, document)
                chapters.extend(content_chapters)
                self.logger.info(f"コンテンツから{len(content_chapters)}章を推測")
            
            # 章番号の正規化
            self._normalize_chapter_numbers(chapters)
            
            return chapters
            
        except Exception as e:
            error_msg = f"章解析エラー: {str(e)}"
            self.logger.error(error_msg)
            raise ChapterAnalysisError(error_msg, document.file_path, str(e))
    
    def _extract_chapters_from_toc(self, book, document: Document) -> List[Chapter]:
        """目次から章抽出（安全性強化）"""
        chapters = []
        
        try:
            toc = book.toc
            if not toc:
                return chapters
            
            chapter_num = 1
            
            def process_toc_item(item, depth=0):
                nonlocal chapter_num
                
                try:
                    if isinstance(item, (tuple, list)) and len(item) >= 2:
                        # (Link, title) または (Section, children) の場合
                        if hasattr(item[0], 'href'):  # Link object
                            link = item[0]
                            title = str(item[1]) if len(item) > 1 else ''
                            chapters.append(self._create_chapter_from_link(
                                link, title, chapter_num, document
                            ))
                            chapter_num += 1
                        elif isinstance(item[1], list):  # Section with children
                            for child in item[1]:
                                process_toc_item(child, depth + 1)
                    elif hasattr(item, 'href'):  # Direct Link object
                        chapters.append(self._create_chapter_from_link(
                            item, getattr(item, 'title', ''), chapter_num, document
                        ))
                        chapter_num += 1
                    elif isinstance(item, list):  # List of items
                        for subitem in item:
                            process_toc_item(subitem, depth + 1)
                            
                except Exception as e:
                    self.logger.warning(f"目次項目処理エラー: {e}")
            
            # TOCを再帰的に処理
            if isinstance(toc, list):
                for item in toc:
                    process_toc_item(item)
            else:
                process_toc_item(toc)
                
        except Exception as e:
            self.logger.warning(f"目次解析エラー: {e}")
        
        return chapters
    
    def _create_chapter_from_link(self, link, title: str, chapter_num: int, document: Document) -> Chapter:
        """リンクから章オブジェクト作成"""
        try:
            href = getattr(link, 'href', '') if hasattr(link, 'href') else str(link)
            title = str(title).strip() if title else f"Chapter {chapter_num}"
            
            # 安全なタイトル生成
            safe_title = sanitize_filename(title)
            
            return Chapter(
                document_id=document.id,
                chapter_number=chapter_num,
                title=safe_title,
                xpath=href,
                detected_method=ChapterDetectionMethod.AUTO,
                confidence_score=0.8
            )
            
        except Exception as e:
            self.logger.warning(f"章作成エラー: {e}")
            return Chapter(
                document_id=document.id,
                chapter_number=chapter_num,
                title=f"Chapter {chapter_num}",
                detected_method=ChapterDetectionMethod.AUTO,
                confidence_score=0.3
            )
    
    def _extract_chapters_from_content(self, book, document: Document) -> List[Chapter]:
        """コンテンツから章推測（安全性強化）"""
        chapters = []
        
        try:
            items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            
            for idx, item in enumerate(items):
                try:
                    # コンテンツの安全な取得
                    content = self._safe_get_item_content(item)
                    if not content:
                        continue
                    
                    # HTMLパース（安全）
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # 見出しを検索
                    title = self._extract_title_from_content(soup, item)
                    
                    if title:
                        chapter = Chapter(
                            document_id=document.id,
                            chapter_number=idx + 1,
                            title=sanitize_filename(title),
                            xpath=getattr(item, 'file_name', f'item_{idx}'),
                            detected_method=ChapterDetectionMethod.AUTO,
                            confidence_score=0.6
                        )
                        chapters.append(chapter)
                        
                except Exception as e:
                    self.logger.warning(f"コンテンツ項目処理エラー (idx={idx}): {e}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"コンテンツ解析エラー: {e}")
        
        return chapters
    
    def _safe_get_item_content(self, item) -> Optional[str]:
        """アイテムコンテンツの安全な取得"""
        try:
            if hasattr(item, 'get_content'):
                content = item.get_content()
                if isinstance(content, bytes):
                    # エンコーディングを推測して安全にデコード
                    try:
                        return content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            return content.decode('latin-1')
                        except:
                            return content.decode('utf-8', errors='ignore')
                return str(content)
        except Exception as e:
            self.logger.debug(f"コンテンツ取得エラー: {e}")
        return None
    
    def _extract_title_from_content(self, soup, item) -> str:
        """コンテンツからタイトル抽出"""
        try:
            # 見出しタグから検索
            for tag_name in ['h1', 'h2', 'h3', 'title']:
                tags = soup.find_all(tag_name)
                for tag in tags:
                    if tag.get_text(strip=True):
                        return tag.get_text(strip=True)
            
            # ファイル名から推測
            if hasattr(item, 'file_name'):
                return Path(item.file_name).stem
                
        except Exception as e:
            self.logger.debug(f"タイトル抽出エラー: {e}")
        
        return ''
    
    def _normalize_chapter_numbers(self, chapters: List[Chapter]) -> None:
        """章番号の正規化"""
        for idx, chapter in enumerate(chapters):
            chapter.chapter_number = idx + 1
    
    def split_epub_by_chapters(self, document: Document, chapters: List[Chapter], 
                             settings: SplitSettings) -> List[str]:
        """EPUB章別分割実行（エラーハンドリング強化）"""
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
            
            if requires_conversion and settings.output_format == OutputFormat.PDF:
                # EPUB → PDF変換は将来実装
                self.logger.warning("EPUB→PDF変換は現在サポートされていません。EPUB形式で出力します。")
                output_extension = ".epub"
            
            # 元のEPUBファイル読み込み
            source_book = epub.read_epub(document.file_path)
            
            for chapter in chapters:
                try:
                    if not chapter.xpath:
                        self.logger.warning(f"章のパスが無効です: {chapter.title}")
                        continue
                    
                    # 安全なファイル名生成
                    safe_filename = get_safe_chapter_filename(
                        document.title, 
                        chapter.chapter_number, 
                        chapter.title,
                        output_extension
                    )
                    
                    output_path = ensure_unique_filename(output_dir / safe_filename)
                    
                    # 章の抽出と保存
                    success = self._extract_and_save_chapter(
                        source_book, chapter, output_path, settings
                    )
                    
                    if success:
                        chapter.output_file_path = str(output_path)
                        chapter.split_status = ProcessingStatus.SUCCESS
                        output_files.append(str(output_path))
                        self.logger.info(f"章分割完了: {chapter.title} -> {output_path.name}")
                    else:
                        chapter.split_status = ProcessingStatus.ERROR
                        self.logger.error(f"章分割失敗: {chapter.title}")
                        
                except Exception as e:
                    self.logger.warning(f"章処理エラー ({chapter.title}): {e}")
                    chapter.split_status = ProcessingStatus.ERROR
                    continue
            
        except Exception as e:
            error_msg = f"EPUB分割処理エラー: {str(e)}"
            self.logger.error(error_msg)
            raise FileProcessingError(error_msg, document.file_path, str(e))
        
        return output_files
    
    def _extract_and_save_chapter(self, source_book, chapter: Chapter, 
                                output_path: Path, settings: SplitSettings) -> bool:
        """章の抽出と保存（安全性強化）"""
        try:
            # 新しいEPUBブック作成
            new_book = epub.EpubBook()
            
            # メタデータ設定
            if settings.preserve_metadata:
                self._copy_metadata(source_book, new_book, chapter)
            
            # 章のコンテンツを取得
            chapter_items = self._get_chapter_items(source_book, chapter)
            
            if not chapter_items:
                self.logger.warning(f"章のコンテンツが見つかりません: {chapter.title}")
                return False
            
            # コンテンツをコピー
            for item in chapter_items:
                try:
                    new_book.add_item(item)
                except Exception as e:
                    self.logger.warning(f"アイテム追加エラー: {e}")
            
            # スパインとTOC作成
            self._create_spine_and_toc(new_book, chapter_items, chapter)
            
            # ファイル保存
            epub.write_epub(str(output_path), new_book)
            
            return True
            
        except Exception as e:
            self.logger.error(f"章抽出・保存エラー: {e}")
            return False
    
    def _copy_metadata(self, source_book, new_book, chapter: Chapter) -> None:
        """メタデータの安全なコピー"""
        try:
            # 基本メタデータをコピー
            metadata_fields = ['DC', 'title', 'creator', 'language', 'publisher']
            
            for namespace in ['DC']:
                try:
                    metadata_items = source_book.metadata.get(namespace, {})
                    for key, values in metadata_items.items():
                        if values and len(values) > 0:
                            new_book.set_identifier(str(values[0][0]))
                            break
                except:
                    pass
            
            # 章固有のメタデータ設定
            new_book.set_title(f"{chapter.title}")
            new_book.set_language('ja')  # デフォルト言語
            
        except Exception as e:
            self.logger.debug(f"メタデータコピーエラー: {e}")
    
    def _get_chapter_items(self, book, chapter: Chapter) -> List:
        """章に関連するアイテムを取得（安全性強化）"""
        items = []
        
        try:
            # 全ドキュメントアイテムを取得
            all_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            
            # 章のxpathに一致するアイテムを検索
            for item in all_items:
                try:
                    item_name = getattr(item, 'file_name', '')
                    if chapter.xpath in item_name or item_name in chapter.xpath:
                        items.append(item)
                        break
                except:
                    continue
            
            # 見つからない場合は最初のアイテムを使用
            if not items and all_items:
                items = [all_items[0]]
                
        except Exception as e:
            self.logger.warning(f"章アイテム取得エラー: {e}")
        
        return items
    
    def _create_spine_and_toc(self, book, items: List, chapter: Chapter) -> None:
        """スパインとTOCの作成"""
        try:
            # スパイン設定
            book.spine = ['nav'] + [item for item in items]
            
            # ナビゲーション設定
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
        except Exception as e:
            self.logger.debug(f"スパイン・TOC作成エラー: {e}")
