"""OpenSearch RAG store for AIOps knowledge base"""

import json
import boto3
from typing import Dict, List, Optional, Any
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth


class RAGStore:
    """OpenSearch store for RAG knowledge base"""
    
    def __init__(self, domain_endpoint: str, region: str = "ap-southeast-1"):
        self.domain_endpoint = domain_endpoint
        self.region = region
        self.index_name = "aiops-knowledge"
        
        # Set up OpenSearch client with AWS auth
        credentials = boto3.Session().get_credentials()
        awsauth = AWSRequestsAuth(credentials, region, 'es')
        
        self.client = OpenSearch(
            hosts=[{'host': domain_endpoint.replace('https://', ''), 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        
        # Create index if it doesn't exist
        self._create_index_if_not_exists()
    
    def _create_index_if_not_exists(self):
        """Create the knowledge base index if it doesn't exist"""
        if not self.client.indices.exists(index=self.index_name):
            index_body = {
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "category": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": 1536  # OpenAI embedding dimension
                        }
                    }
                }
            }
            
            self.client.indices.create(index=self.index_name, body=index_body)
            print(f"Created index: {self.index_name}")
    
    def add_document(self, doc_id: str, title: str, content: str, 
                    category: str = "general", tags: List[str] = None,
                    embedding: List[float] = None) -> bool:
        """Add a document to the knowledge base"""
        try:
            document = {
                "title": title,
                "content": content,
                "category": category,
                "tags": tags or [],
                "created_at": "now",
                "updated_at": "now"
            }
            
            if embedding:
                document["embedding"] = embedding
            
            response = self.client.index(
                index=self.index_name,
                id=doc_id,
                body=document
            )
            
            return response["result"] in ["created", "updated"]
            
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def search_documents(self, query: str, category: Optional[str] = None,
                        size: int = 10) -> List[Dict[str, Any]]:
        """Search documents using text search"""
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "content"],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                },
                "size": size,
                "sort": [{"_score": {"order": "desc"}}]
            }
            
            if category:
                search_body["query"]["bool"]["filter"] = [
                    {"term": {"category": category}}
                ]
            
            response = self.client.search(index=self.index_name, body=search_body)
            
            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "title": hit["_source"]["title"],
                    "content": hit["_source"]["content"],
                    "category": hit["_source"]["category"],
                    "tags": hit["_source"]["tags"]
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    def vector_search(self, embedding: List[float], category: Optional[str] = None,
                     size: int = 10) -> List[Dict[str, Any]]:
        """Search documents using vector similarity"""
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": embedding,
                                        "k": size
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": size
            }
            
            if category:
                search_body["query"]["bool"]["filter"] = [
                    {"term": {"category": category}}
                ]
            
            response = self.client.search(index=self.index_name, body=search_body)
            
            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "title": hit["_source"]["title"],
                    "content": hit["_source"]["content"],
                    "category": hit["_source"]["category"],
                    "tags": hit["_source"]["tags"]
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        try:
            response = self.client.get(index=self.index_name, id=doc_id)
            
            if response["found"]:
                return {
                    "id": response["_id"],
                    "title": response["_source"]["title"],
                    "content": response["_source"]["content"],
                    "category": response["_source"]["category"],
                    "tags": response["_source"]["tags"],
                    "created_at": response["_source"]["created_at"],
                    "updated_at": response["_source"]["updated_at"]
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting document: {e}")
            return None
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the knowledge base"""
        try:
            response = self.client.delete(index=self.index_name, id=doc_id)
            return response["result"] == "deleted"
            
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False
    
    def add_investigation_knowledge(self, investigation_id: str, 
                                  alarm_type: str, root_causes: List[str],
                                  solutions: List[str]) -> bool:
        """Add investigation results as knowledge"""
        title = f"Investigation: {alarm_type}"
        content = f"""
        Alarm Type: {alarm_type}
        Investigation ID: {investigation_id}
        
        Root Causes Found:
        {chr(10).join(f"- {cause}" for cause in root_causes)}
        
        Solutions Applied:
        {chr(10).join(f"- {solution}" for solution in solutions)}
        """
        
        return self.add_document(
            doc_id=f"investigation_{investigation_id}",
            title=title,
            content=content,
            category="investigation",
            tags=[alarm_type, "root_cause", "solution"]
        )
    
    def search_similar_investigations(self, alarm_type: str, 
                                    symptoms: List[str]) -> List[Dict[str, Any]]:
        """Search for similar past investigations"""
        query = f"{alarm_type} {' '.join(symptoms)}"
        return self.search_documents(
            query=query,
            category="investigation",
            size=5
        )