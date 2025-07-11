from fastapi import HTTPException
from config.models.app import CollectionRequest
from config.logger import get_logger
from qdrant.app import QdrantConnection

logger = get_logger(__name__)

def create_qdrant_collection(request: CollectionRequest):
    """Create a new collection in Qdrant"""
    try:
        qdrant_conn = QdrantConnection()

        qdrant_conn.create_collection(
            collection_name=request.collection_name, 
            vector_size=request.vector_size, 
            distance=request.distance
        )

        return {
            "success": True,
            "message": f"Collection '{request.collection_name}' created successfully",
            "collection_name": request.collection_name,
            "vector_size": request.vector_size,
            "distance": request.distance
        }
        
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))