# QuickSee - 智能新闻助手

QuickSee 是一个基于 AI 的智能新闻聊天助手，能够帮助用户快速了解最新新闻信息，解答与新闻相关的问题，并提供引用来源。该项目使用 Flask 作为后端框架，结合现代化的前端技术，提供了友好的用户界面和流畅的交互体验。

![QuickSee Logo](frontend/static/img/quicksee_logo.png)

## 主要功能

- **智能问答**：基于大语言模型，回答用户关于新闻的问题
- **RSS 订阅**：支持多种 RSS 源，实时获取最新资讯
- **引用追溯**：查看 AI 回答的信息来源和引用
- **历史对话**：保存和回顾历史对话内容
- **响应式设计**：支持各种设备和屏幕尺寸

## 技术架构

- **后端**：Python + Flask
- **前端**：HTML5 + CSS3 + JavaScript
- **数据存储**：FAISS 向量索引
- **AI 模型**：大语言模型 API 集成
- **新闻源**：RSS 解析与存储

## 安装指南

### 前提条件

- Python 3.7+
- pip 包管理器
- Node.js 和 npm（可选，用于前端开发）

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/yourusername/quicksee.git
cd quicksee
```

2. 创建虚拟环境（推荐）

```bash
python -m venv venv
source venv/bin/activate  # 在 Windows 上使用 venv\Scripts\activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 配置环境变量

创建一个 `.env` 文件在项目根目录，参考下方 [环境变量配置](#环境变量配置) 部分。

5. 初始化 RSS 源

将 RSS 源添加到 `RSS_source.json` 文件中，格式参考下方说明。

6. 启动服务

```bash
./start_website.sh  # 在 Linux/Mac 上
# 或者
python run_website.py
```

## 环境变量配置

创建 `.env` 文件，包含以下配置项：

```
# 服务器配置
FLASK_APP=server.py
HOST=127.0.0.1
PORT=5002
DEBUG=false

# 文件路径配置
RSS_DIR=data/rss
FAISS_INDEX_PATH=data/faiss_index

# API 密钥（根据您使用的 LLM 服务选择配置）
OPENAI_API_KEY=your_openai_key
# 或
DASHSCOPE_API_KEY=your_dashscope_key
```

## RSS 源配置

在项目根目录下创建或修改 `RSS_source.json` 文件：

```json
[
  {
    "url": "http://example.com/rss.xml",
    "title": "示例新闻源",
    "简介": "示例新闻源的描述",
    "属性": "example",
    "uuid": "生成的唯一标识符"
  }
]
```

您也可以通过网页界面中的"添加 RSS 源"功能添加新的 RSS 源。

## 开发指南

### 项目结构

```
quicksee/
├── backend/               # 后端代码
│   ├── api/               # API 路由
│   ├── app_modules/       # 应用模块
│   └── templates/         # 模板文件
├── frontend/              # 前端代码
│   ├── static/            # 静态资源
│   │   ├── css/           # 样式表
│   │   ├── js/            # JavaScript 文件
│   │   └── img/           # 图片资源
│   └── templates/         # HTML 模板
├── data/                  # 数据文件
│   ├── rss/               # RSS 缓存文件
│   └── faiss_index/       # FAISS 索引
├── .env                   # 环境变量（本地开发）
├── requirements.txt       # Python 依赖
├── run_website.py         # 启动脚本
└── start_website.sh       # 启动脚本（Linux/Mac）
```

### 添加新功能

1. **添加新的 API 端点**：在 `backend/api/` 目录下修改或创建路由文件
2. **添加新的前端组件**：在 `frontend/static/js/` 和 `frontend/templates/` 中添加组件
3. **扩展 LLM 集成**：在 `backend/app_modules/llm/` 目录中进行修改

## 故障排除

### 常见问题

1. **服务无法启动**：
   - 检查 `.env` 文件配置是否正确
   - 确认 Python 版本是否符合要求
   - 验证所有依赖是否已安装

2. **RSS 内容不更新**：
   - 确认 RSS 源 URL 是否有效
   - 检查网络连接状态
   - 验证 RSS 目录权限

3. **AI 回答错误或无响应**：
   - 检查 API 密钥配置是否正确
   - 确认网络连接状态
   - 验证 FAISS 索引是否已正确构建

## 贡献指南

1. Fork 该仓库
2. 创建您的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件

## 联系方式

如有任何问题或建议，请通过 GitHub Issues 联系我们。
