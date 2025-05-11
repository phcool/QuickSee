import json
import time
from typing import List, Dict, Any, Optional
import logging
import os
import importlib.util
import sys
import numpy as np
from enum import Enum
import requests
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from aliyunsdkcore.request import CommonRequest

from backend.app_modules.config import ALIBABA_ACCESS_KEY, ALIBABA_ACCESS_SECRET, ALIBABA_REGION, EMBEDDING_MODEL


class AlibabaEmbeddingService:
    """Interface with Alibaba Cloud's text embedding service."""
    
    def __init__(
        self,
        access_key: str = ALIBABA_ACCESS_KEY,
        access_secret: str = ALIBABA_ACCESS_SECRET,
        region: str = ALIBABA_REGION,
        model_name: str = EMBEDDING_MODEL
    ):
        self.access_key = access_key
        self.access_secret = access_secret
        self.region = region
        self.model_name = model_name
        
        # Initialize Alibaba Cloud client
        credentials = AccessKeyCredential(self.access_key, self.access_secret)
        self.client = AcsClient(region_id=self.region, credential=credentials)
        
    def _create_embedding_request(self, texts: List[str]) -> CommonRequest:
        """Create a CommonRequest for text embedding."""
        request = CommonRequest()
        request.set_domain("dashscope.aliyuncs.com")
        request.set_method("POST")
        request.set_protocol_type("https")
        request.set_version("2023-06-30")
        request.set_action_name("CreateEmbeddings")
        
        request.add_header("Content-Type", "application/json")
        
        # Set request body
        request_body = {
            "model": self.model_name,
            "input": {
                "texts": texts
            }
        }
        
        request.set_content(json.dumps(request_body).encode("utf-8"))
        return request
    
    def get_embeddings(self, texts: List[str], retry_count: int = 3) -> List[List[float]]:
        """Get embeddings for a list of texts."""
        if not texts:
            return []
        
        # Split texts into batches of 16 (API limit)
        batch_size = 16
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            
            # Retry logic
            for attempt in range(retry_count):
                try:
                    request = self._create_embedding_request(batch_texts)
                    response = self.client.do_action_with_exception(request)
                    response_json = json.loads(response.decode("utf-8"))
                    
                    if "output" in response_json and "embeddings" in response_json["output"]:
                        batch_embeddings = [item["embedding"] for item in response_json["output"]["embeddings"]]
                        all_embeddings.extend(batch_embeddings)
                        break
                    else:
                        print(f"Unexpected response format: {response_json}")
                        if attempt == retry_count - 1:
                            raise ValueError("Failed to get embeddings after multiple attempts")
                except Exception as e:
                    print(f"Error getting embeddings (attempt {attempt + 1}/{retry_count}): {e}")
                    if attempt == retry_count - 1:
                        raise
                    time.sleep(1)  # Wait before retrying
        
        return all_embeddings
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text."""
        embeddings = self.get_embeddings([text])
        if embeddings:
            return embeddings[0]
        return []
    
    def create_embedding_dict(self, texts_with_ids: Dict[str, str]) -> Dict[str, List[float]]:
        """Create a dictionary of embeddings keyed by their IDs."""
        ids = list(texts_with_ids.keys())
        texts = list(texts_with_ids.values())
        
        embeddings = self.get_embeddings(texts)
        
        return {id_key: embedding for id_key, embedding in zip(ids, embeddings)}


# Create a singleton instance
embedding_service = AlibabaEmbeddingService() 