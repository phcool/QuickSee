import os
import re
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import glob

from backend.app_modules.config import RSS_DIR


@dataclass
class NewsArticle:
    """Data class for storing news article information."""
    title: str
    link: str
    pub_date: str
    content: str
    source_file: str
    metadata: Optional[Dict] = None


class RSSParser:
    """Parser for RSS files in text format."""
    
    def __init__(self, rss_directory: str = RSS_DIR):
        self.rss_directory = rss_directory
    
    def get_all_rss_files(self) -> List[str]:
        """Get all RSS files from the RSS directory."""
        return glob.glob(os.path.join(self.rss_directory, "**/*.txt"), recursive=True)
    
    def parse_file(self, file_path: str) -> NewsArticle:
        """Parse a single RSS file and extract information."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title, link, and publication date using regex
        title_match = re.search(r'标题: (.*?)(?:\n|$)', content)
        link_match = re.search(r'链接: (.*?)(?:\n|$)', content)
        date_match = re.search(r'发布时间: (.*?)(?:\n|$)', content)
        
        title = title_match.group(1) if title_match else ""
        link = link_match.group(1) if link_match else ""
        pub_date = date_match.group(1) if date_match else ""
        
        # Extract main content (everything after the metadata)
        main_content = ""
        content_lines = content.split('\n')
        start_idx = 0
        
        # Find where the main content starts (after metadata)
        for i, line in enumerate(content_lines):
            if line.strip() == "" and i > 3:  # Assume metadata ends with empty line
                start_idx = i + 1
                break
        
        if start_idx > 0 and start_idx < len(content_lines):
            main_content = "\n".join(content_lines[start_idx:])
            
            # Clean up footer content if present
            footer_patterns = [
                "分享让更多人看到",
                "人民日报社概况",
                "版权所有"
            ]
            
            for pattern in footer_patterns:
                if pattern in main_content:
                    main_content = main_content[:main_content.find(pattern)]
        
        return NewsArticle(
            title=title,
            link=link,
            pub_date=pub_date,
            content=main_content.strip(),
            source_file=file_path,
            metadata={"file_path": file_path}
        )
    
    def parse_all_files(self) -> List[NewsArticle]:
        """Parse all RSS files in the directory."""
        articles = []
        for file_path in self.get_all_rss_files():
            try:
                article = self.parse_file(file_path)
                articles.append(article)
            except Exception as e:
                print(f"Error parsing file {file_path}: {e}")
        
        return articles
    
    def export_to_json(self, output_path: str) -> None:
        """Export all parsed articles to a JSON file."""
        articles = self.parse_all_files()
        
        # Convert dataclass objects to dictionaries
        articles_dict = [
            {
                "title": article.title,
                "link": article.link,
                "pub_date": article.pub_date,
                "content": article.content,
                "source_file": article.source_file,
                "metadata": article.metadata
            }
            for article in articles
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(articles_dict, f, ensure_ascii=False, indent=2) 