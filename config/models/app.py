from typing import Any, Dict, List, Optional
from pydantic import BaseModel

VECTOR_SIZE = 384

class EmbedRequest(BaseModel):
    texts: List[str]
    collection_name: str
    metadata: Optional[List[Dict[str, Any]]] = None
    ids: Optional[List[str]] = None

class CollectionRequest(BaseModel):
    collection_name: str
    vector_size: Optional[int] = VECTOR_SIZE
    distance: Optional[str] = "Cosine"

class EmbedResponse(BaseModel):
    success: bool
    message: str
    ids: List[str]
    count: int

class MultiplePointsRequest(BaseModel):
    ids: List[Any]

# Add this request model (add this after your existing models)
class FetchArticlesRequest(BaseModel):
    referenceId: str
    relatedIds: List[str]

class ArticleData(BaseModel):
    embedding_id: str
    url: str
    title: str

class FetchArticlesResponse(BaseModel):
    referenceId: Optional[ArticleData]
    relatedIds: List[ArticleData]

class CompareItem(BaseModel):
    referenceId: str
    url: str
    title: str
    filtered_articles: List[ArticleData]

class CompareResponse(BaseModel):
    results: List[CompareItem]
    total_processed: int
