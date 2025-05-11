# 新闻聊天系统 (News Chat System)

基于RAG (Retrieval-Augmented Generation) 的新闻检索与智能问答系统，支持RSS新闻文件解析、语义搜索和AI对话功能。

## 功能特点

- 解析RSS新闻文件，支持多种格式
- 使用阿里云 `text-embedding-v3` 生成文本嵌入
- 基于FAISS的高效语义搜索
- 实现RAG增强大模型回答质量
- 提供命令行和Web界面两种使用方式

## 快速开始

### 前提条件

1. Python 3.8+
2. [阿里云AccessKey](https://help.aliyun.com/document_detail/53045.html)（用于DashScope API）
3. 对于macOS用户，需要使用conda安装FAISS

### 安装

1. 克隆仓库并进入目录
   ```bash
   git clone <repository-url>
   cd news-chat-system
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```
   
   macOS用户需要额外安装FAISS:
   ```bash
   conda install -c conda-forge faiss-cpu
   ```

3. 创建环境变量文件 `.env`
   ```
   DASHSCOPE_API_KEY=your_api_key_here
   ```

### 使用方式

#### 命令行模式

1. 索引RSS文件
   ```bash
   python -m app.main index --rss-dir data/rss
   ```

2. 搜索相似文章
   ```bash
   python -m app.main search "你的搜索关键词"
   ```

3. 启动聊天模式
   ```bash
   python -m app.main chat
   ```

4. 一键运行脚本
   ```bash
   python run_news_chat.py
   ```

#### Web模式 (新)

1. 启动Web服务器
   ```bash
   ./start_website.sh
   ```
   
   或使用Python直接启动:
   ```bash
   python run_website.py
   ```

2. 在浏览器中访问 `http://127.0.0.1:5000`

3. Web功能:
   - 主页: 显示最新新闻和索引管理
   - 搜索页: 根据关键词搜索新闻
   - 聊天页: 与AI助手进行聊天

### 自定义选项

Web服务器提供以下选项:

```bash
./start_website.sh --help

选项:
  --host=HOST         设置监听主机 (默认: 127.0.0.1)
  --port=PORT         设置监听端口 (默认: 5000)
  --debug             启用调试模式
  --rss-dir=DIR       设置RSS文件目录 (默认: data/rss)
  --faiss-index=FILE  设置FAISS索引文件 (默认: data/faiss_index/news.index)
```

## RSS文件格式

系统支持的RSS文件需包含以下元素:
- title: 文章标题
- link: 文章链接
- pubDate: 发布日期
- content/description: 文章内容

## 项目结构

```
news-chat-system/
├── app/                # 核心应用代码
│   ├── config.py       # 配置文件
│   ├── llm/            # 大语言模型集成
│   ├── parser/         # RSS解析器
│   ├── vectordb/       # 向量数据库
│   └── main.py         # 命令行入口
├── backend/            # Web后端
│   ├── api/            # API路由
│   └── app.py          # Flask应用
├── frontend/           # Web前端
│   ├── static/         # 静态文件 (CSS/JS)
│   └── templates/      # HTML模板
├── data/               # 数据目录
│   ├── rss/            # RSS文件
│   └── faiss_index/    # FAISS索引
├── run_news_chat.py    # 命令行运行脚本
├── run_website.py      # Web服务启动脚本
├── start_website.sh    # Web服务启动Shell脚本
└── requirements.txt    # 依赖列表
```

## 故障排除

### FAISS安装问题

- 如果出现 `ModuleNotFoundError: No module named 'faiss'`，请查看以下解决方案:
  - 对于macOS用户: `conda install -c conda-forge faiss-cpu`
  - 对于其他用户: `pip install faiss-cpu`
  - 如果上述方法都不成功，请考虑[从源代码编译](https://github.com/facebookresearch/faiss/blob/main/INSTALL.md)

### API连接问题

- 如果出现API连接问题，请检查:
  - `.env` 文件中的API密钥是否正确
  - 网络连接是否正常
  - API服务是否可用

## 许可证

本项目使用 MIT 许可证 