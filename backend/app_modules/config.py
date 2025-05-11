import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Alibaba Cloud API configurations
ALIBABA_ACCESS_KEY = os.getenv("ALIBABA_ACCESS_KEY", "")
ALIBABA_ACCESS_SECRET = os.getenv("ALIBABA_ACCESS_SECRET", "")
ALIBABA_REGION = os.getenv("ALIBABA_REGION", "cn-hangzhou")

# Embedding model settings
EMBEDDING_MODEL = os.getenv("LLM_EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))

# LLM model settings
LLM_MODEL = os.getenv("LLM_CONVERSATION_MODEL", "qwen-3")

# 项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# RSS file settings
RSS_DIR = os.getenv("RSS_DIR", os.path.join(ROOT_DIR, "data", "rss"))

# FAISS index settings
# 与run_news_chat.py保持一致，指向根目录下的data/faiss_index
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", os.path.join(ROOT_DIR, "data", "faiss_index"))

# Chunk size for text splitting
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200 