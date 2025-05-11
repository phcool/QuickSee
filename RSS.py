import feedparser
import datetime
import os
import requests
from bs4 import BeautifulSoup
import re
import time
import json
import uuid
import shutil
import sys
import asyncio
from pathlib import Path

# 导入向量索引相关模块
from backend.app_modules.parsers.rss_parser import RSSParser
from backend.app_modules.llm.llm_integration import get_embeddings
from backend.app_modules.vectordb.faiss_store import vector_store

def get_uuid_from_url(url):
    """从URL生成唯一的UUID"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url))

def get_uuid_from_title(title):
    """从标题生成唯一的UUID"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, title))

def is_within_days(date_str, days=30):
    """检查日期是否在指定天数内"""
    if not date_str:
        return False
    
    try:
        article_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        current_date = datetime.datetime.now()
        delta = current_date - article_date
        return delta.days <= days
    except Exception as e:
        print(f"日期检查错误: {e}")
        return False

def clean_old_articles(directory, days=30):
    """删除指定目录中超过30天的文章"""
    try:
        if not os.path.exists(directory):
            return
            
        for date_dir in os.listdir(directory):
            date_path = os.path.join(directory, date_dir)
            if os.path.isdir(date_path) and re.match(r'\d{4}-\d{2}-\d{2}', date_dir):
                if not is_within_days(date_dir, days):
                    print(f"删除过期目录: {date_path}")
                    shutil.rmtree(date_path)
    except Exception as e:
        print(f"清理旧文章时出错: {e}")

def get_latest_date_in_directory(directory):
    """获取目录中最新的日期文件夹"""
    if not os.path.exists(directory):
        return None
        
    date_dirs = [d for d in os.listdir(directory) 
                 if os.path.isdir(os.path.join(directory, d)) 
                 and re.match(r'\d{4}-\d{2}-\d{2}', d)]
    
    if not date_dirs:
        return None
        
    # 按日期排序，返回最新的日期
    date_dirs.sort(reverse=True)
    return date_dirs[0]

def update_index():
    """
    更新FAISS向量索引
    读取RSS文件，生成向量嵌入，更新索引
    """
    try:
        print("开始更新向量索引...")
        
        # 从RSS目录读取文件
        rss_dir = os.getenv("RSS_DIR", os.path.join(".", "data", "rss"))
        
        # 确保目录存在
        if not os.path.exists(rss_dir):
            os.makedirs(rss_dir, exist_ok=True)
            print(f"RSS目录 ({rss_dir}) 不存在，已创建。但没有RSS文件可索引。")
            return False
        
        # 解析RSS文件
        parser = RSSParser(rss_directory=rss_dir)
        articles = parser.parse_all_files()
        
        if len(articles) == 0:
            print(f"在 {rss_dir} 中没有找到RSS文件，无法更新索引。")
            return False
        
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 获取文章内容的向量嵌入
        texts = [article.content for article in articles]
        embeddings = loop.run_until_complete(get_embeddings(texts))
        loop.close()
        
        if embeddings is None:
            print("生成向量嵌入失败。请检查DashScope API配置。")
            return False
        
        # 添加到向量存储
        vector_store.add_articles(articles, embeddings)
        
        # 获取索引统计信息
        stats = None
        if vector_store and hasattr(vector_store, 'get_stats'):
            stats = vector_store.get_stats()
            print(f"索引统计: {stats}")
        
        print(f"成功索引了 {len(articles)} 篇文章。")
        return True
        
    except Exception as e:
        print(f"更新索引时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def fetch_and_save_rss_data(rss_info):
    """
    从指定的RSS获取数据并保存文章内容
    返回生成的UUID
    """
    rss_url = rss_info.get('url')
    rss_title = rss_info.get('title', '未命名')
    rss_type = rss_info.get('属性', '')
    
    # 生成UUID并创建目录
    url_uuid = get_uuid_from_url(rss_url)
    base_dir = os.path.join(".", "./data/rss", url_uuid)
    os.makedirs(base_dir, exist_ok=True)
    
    # 清理旧文章
    clean_old_articles(base_dir)
    
    # 检查最新日期，如果今天已经更新过，则跳过
    latest_date = get_latest_date_in_directory(base_dir)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 标记是否有新文章被添加，用于判断是否需要更新索引
    new_content_added = False
    
    if latest_date == today:
        print(f"RSS源 '{rss_title}' 今天已经更新过，跳过更新")
        return url_uuid, new_content_added
    
    # 解析RSS feed
    print(f"正在获取RSS Feed: {rss_title} ({rss_url})")
    feed = feedparser.parse(rss_url)
    
    # 检查feed是否成功解析
    if not feed or not hasattr(feed, 'feed') or not feed.entries:
        print(f"无法解析RSS feed或feed为空: {rss_url}")
        if hasattr(feed, 'bozo_exception'):
            print(f"Feed解析错误: {feed.bozo_exception}")
        return url_uuid, new_content_added
    
    # 打印feed基本信息
    print(f"Feed标题: {feed.feed.get('title', '无标题')}")
    print(f"Feed链接: {feed.feed.get('link', '无链接')}")
    print(f"文章数量: {len(feed.entries)}")
    print("\n" + "-"*50 + "\n")
    
    # 遍历每篇文章
    for i, entry in enumerate(feed.entries, 1):
        try:
            title = entry.get('title', f'无标题文章_{i}')
            print(f"处理文章 {i}/{len(feed.entries)}: {title}")
            
            # 获取发布日期，如果没有则使用当前日期
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            if 'published_parsed' in entry and entry.published_parsed:
                try:
                    date_str = time.strftime("%Y-%m-%d", entry.published_parsed)
                except Exception as e:
                    print(f"解析日期出错，使用当前日期: {e}")
            
            # 跳过30天前的文章
            if not is_within_days(date_str):
                print(f"跳过30天前的文章: {title} (发布于 {date_str})")
                continue
                
            # 使用标题生成UUID作为文件名
            title_uuid = get_uuid_from_title(title)
            
            # 创建保存目录
            save_dir = os.path.join(base_dir, date_str)
            os.makedirs(save_dir, exist_ok=True)
            
            # 文件路径
            file_path = os.path.join(save_dir, f"{title_uuid}.txt")
            
            # 检查文件是否已存在，如果存在则跳过
            if os.path.exists(file_path):
                print(f"文章已存在，跳过: {file_path}")
                continue
            
            # 获取文章完整内容
            article_content = ""
            try:
                # 获取文章标题和链接信息
                article_content += f"标题: {title}\n"
                article_content += f"链接: {entry.get('link', '无链接')}\n"
                article_content += f"发布时间: {entry.get('published', '未知')}\n\n"
                
                # 尝试访问原文链接获取完整内容
                if 'link' in entry:
                    print(f"获取文章内容: {entry.link}")
                    response = requests.get(entry.link, timeout=10)
                    response.encoding = 'utf-8'  # 确保中文正确显示
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 尝试查找文章内容 (针对人民网的常见结构)
                        article = soup.find('div', class_='article') or soup.find('div', id='rwb_zw')
                        
                        if article:
                            # 获取文章段落
                            paragraphs = article.find_all('p')
                            for p in paragraphs:
                                article_content += p.get_text().strip() + "\n\n"
                        else:
                            # 如果找不到特定结构，尝试获取所有段落
                            main_content = soup.find('body')
                            if main_content:
                                paragraphs = main_content.find_all('p')
                                for p in paragraphs:
                                    article_content += p.get_text().strip() + "\n\n"
                
                # 如果没有获取到内容或者获取失败，使用RSS中的summary或description
                if not article_content or len(article_content.strip()) <= (len(title) + 50):
                    if 'summary' in entry:
                        article_content += f"摘要:\n{entry.summary}\n\n"
                    elif 'description' in entry:
                        article_content += f"描述:\n{entry.description}\n\n"
                    elif 'content' in entry:
                        for content in entry.content:
                            article_content += f"内容:\n{content.value}\n\n"
                
                # 对于人民网的内容做特殊处理
                if rss_type == "renminwang":
                    # 查找并删除"分享让更多人看到"及其后面的内容
                    share_index = article_content.find("分享让更多人看到")
                    if share_index != -1:
                        print(f"找到'分享让更多人看到'字符串，删除该字符串及其后面的内容")
                        article_content = article_content[:share_index].strip()
                
                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(article_content)
                
                print(f"成功保存文章: {file_path}")
                new_content_added = True
            
            except Exception as e:
                print(f"获取或保存文章时出错: {e}")
                
                # 尝试保存已有的内容
                if article_content:
                    # 对于人民网的内容做特殊处理
                    if rss_type == "renminwang":
                        # 查找并删除"分享让更多人看到"及其后面的内容
                        share_index = article_content.find("分享让更多人看到")
                        if share_index != -1:
                            print(f"找到'分享让更多人看到'字符串，删除该字符串及其后面的内容")
                            article_content = article_content[:share_index].strip()
                    
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(article_content)
                        print(f"已保存部分内容到: {file_path}")
                        new_content_added = True
                    except Exception as inner_e:
                        print(f"保存部分内容时出错: {inner_e}")
        
        except Exception as article_e:
            print(f"处理文章时发生错误: {article_e}")
        
        print("-" * 30)
    
    # 返回UUID和新内容标志，用于更新JSON和决定是否更新索引
    return url_uuid, new_content_added

def add_rss_source(url, title, description=None, attribute=None):
    """
    向JSON文件添加新的RSS源
    
    参数:
    url (str): RSS源的URL
    title (str): RSS源的标题
    description (str, 可选): RSS源的简介
    attribute (str, 可选): RSS源的属性，比如"renminwang"
    
    返回:
    bool: 添加是否成功
    """
    try:
        # 读取现有RSS源
        rss_config_path = "RSS_source.json"
        if os.path.exists(rss_config_path):
            with open(rss_config_path, 'r', encoding='utf-8') as f:
                rss_sources = json.load(f)
        else:
            rss_sources = []
        
        # 检查URL是否已存在
        for source in rss_sources:
            if source.get('url') == url:
                print(f"警告: URL '{url}' 已存在于RSS源列表中")
                return False
        
        # 创建新的RSS源条目
        new_source = {
            "url": url,
            "title": title
        }
        
        # 添加可选字段
        if description:
            new_source["简介"] = description
        if attribute:
            new_source["属性"] = attribute
        
        # 添加到源列表
        rss_sources.append(new_source)
        
        # 保存回JSON文件
        with open(rss_config_path, 'w', encoding='utf-8') as f:
            json.dump(rss_sources, f, ensure_ascii=False, indent=2)
        
        print(f"成功添加RSS源: {title} ({url})")
        return True
        
    except Exception as e:
        print(f"添加RSS源时出错: {e}")
        return False

def update_specific_rss(identifier, identifier_type='url'):
    """
    更新特定RSS源的数据
    
    参数:
    identifier (str): 用于识别RSS源的标识符，可以是URL或标题
    identifier_type (str): 标识符类型，'url'或'title'
    
    返回:
    bool: 更新是否成功
    """
    try:
        # 读取RSS源配置
        rss_config_path = "RSS_source.json"
        if not os.path.exists(rss_config_path):
            print(f"错误：找不到RSS源配置文件: {rss_config_path}")
            return False
            
        with open(rss_config_path, 'r', encoding='utf-8') as f:
            rss_sources = json.load(f)
        
        # 查找匹配的RSS源
        found = False
        for i, rss_info in enumerate(rss_sources):
            if identifier_type == 'url' and rss_info.get('url') == identifier:
                found = True
            elif identifier_type == 'title' and rss_info.get('title') == identifier:
                found = True
            
            if found:
                print(f"找到匹配的RSS源: {rss_info.get('title')} ({rss_info.get('url')})")
                try:
                    # 更新RSS源数据
                    url_uuid, _ = fetch_and_save_rss_data(rss_info)
                    
                    # 更新UUID（如果需要）
                    if 'uuid' not in rss_info or rss_info['uuid'] != url_uuid:
                        rss_sources[i]['uuid'] = url_uuid
                        # 保存回JSON文件
                        with open(rss_config_path, 'w', encoding='utf-8') as f:
                            json.dump(rss_sources, f, ensure_ascii=False, indent=2)
                        print(f"已更新UUID: {url_uuid}")
                    
                    print(f"已成功更新RSS源: {rss_info.get('title')}")
                    return True
                    
                except Exception as e:
                    print(f"更新RSS源时出错: {e}")
                    return False
        
        if not found:
            print(f"找不到匹配的RSS源: {identifier}")
            return False
            
    except Exception as e:
        print(f"更新特定RSS源时出错: {e}")
        return False

def RSS_main():
    """主函数，读取RSS源并处理"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        # 添加新的RSS源
        if command == 'add' and len(sys.argv) >= 4:
            url = sys.argv[2]
            title = sys.argv[3]
            description = sys.argv[4] if len(sys.argv) > 4 else None
            attribute = sys.argv[5] if len(sys.argv) > 5 else None
            add_rss_source(url, title, description, attribute)
            return
            
        # 更新特定RSS源
        elif command == 'update' and len(sys.argv) >= 3:
            identifier = sys.argv[2]
            identifier_type = sys.argv[3].lower() if len(sys.argv) > 3 else 'url'
            if identifier_type not in ['url', 'title']:
                print("错误: 标识符类型必须是'url'或'title'")
                return
            update_specific_rss(identifier, identifier_type)
            return
            
        # 显示使用帮助
        elif command == 'help':
            print("RSS源管理工具使用帮助:")
            print("1. 添加新RSS源: python RSS.py add <url> <title> [简介] [属性]")
            print("2. 更新特定RSS源: python RSS.py update <标识符> [url|title]")
            print("3. 更新所有RSS源: python RSS.py")
            print("4. 仅更新索引: python RSS.py index")
            return
            
        # 仅更新索引
        elif command == 'index':
            print("开始更新索引...")
            update_index()
            return
    
    try:
        # 读取RSS源配置
        rss_config_path = "RSS_source.json"
        if not os.path.exists(rss_config_path):
            print(f"错误：找不到RSS源配置文件: {rss_config_path}")
            return
            
        with open(rss_config_path, 'r', encoding='utf-8') as f:
            rss_sources = json.load(f)
            
        # 确保data目录存在
        os.makedirs("./data/rss", exist_ok=True)
        
        # 标记是否需要更新JSON文件
        json_updated = False
        
        # 标记是否有新内容添加，用于决定是否更新索引
        has_new_content = False
            
        # 处理每个RSS源
        for i, rss_info in enumerate(rss_sources):
            if 'url' not in rss_info:
                print(f"警告：跳过没有URL的RSS源: {rss_info}")
                continue
                
            try:
                # 处理RSS源并获取UUID和新内容标记
                url_uuid, new_content = fetch_and_save_rss_data(rss_info)
                
                # 如果有新内容，设置全局标记
                if new_content:
                    has_new_content = True
                
                # 如果条目中没有uuid属性或uuid已更改，则更新JSON
                if 'uuid' not in rss_info or rss_info['uuid'] != url_uuid:
                    rss_sources[i]['uuid'] = url_uuid
                    json_updated = True
                    print(f"已为RSS源 '{rss_info.get('title', rss_info['url'])}' 更新UUID: {url_uuid}")
                
            except Exception as e:
                print(f"处理RSS源时出错: {rss_info.get('title', rss_info.get('url'))}")
                print(f"错误信息: {e}")
        
        # 如果有更新，将更新后的数据写回JSON文件
        if json_updated:
            try:
                with open(rss_config_path, 'w', encoding='utf-8') as f:
                    json.dump(rss_sources, f, ensure_ascii=False, indent=2)
                print(f"已将更新的UUID信息保存到 {rss_config_path}")
            except Exception as e:
                print(f"保存更新的JSON文件时出错: {e}")
        
        # 如果有新内容添加，或强制更新索引，则更新向量索引
        if has_new_content or '--force-index' in sys.argv:
            print("检测到新内容添加，正在更新向量索引...")
            update_index()
        else:
            print("没有新内容添加，跳过索引更新。")
                
        print("所有RSS源处理完成!")
    except Exception as e:
        print(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    RSS_main()
    # add_rss_source(url="https://feedx.net/rss/guangmingribao.xml", title="光明日报", description="光明日报新闻", attribute="guangmingribao")