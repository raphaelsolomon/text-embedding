from datetime import datetime
import uuid
from config.models.app import EmbedRequest, EmbedResponse
from config.logger import get_logger
from qdrant.app import QdrantConnection
from fastapi import HTTPException
from qdrant_client.models import PointStruct

logger = get_logger(__name__)

async def embed_and_store_to_qdrant(request: EmbedRequest, model=None):
    """Embed texts and store in Qdrant"""
    if model is None:
        raise HTTPException(status_code=503, detail="Embedding model not ready")

    if request.texts is None or len(request.texts) == 0:
        raise HTTPException(status_code=400, detail="No texts provided for embedding")
    
    try:
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(request.texts)} texts")
        embeddings = model.encode(request.texts)
        
        # Generate IDs if not provided
        if request.ids is None:
            point_ids = [str(uuid.uuid4()) for _ in request.texts]
        else:
            if len(request.ids) != len(request.texts):
                raise HTTPException(status_code=400, detail="Number of IDs must match number of texts")
            point_ids = request.ids
        
        # Prepare metadata
        if request.metadata is None:
            metadata = [{"text": text, "timestamp": datetime.now().isoformat()} for text in request.texts]
        else:
            if len(request.metadata) != len(request.texts):
                raise HTTPException(status_code=400, detail="Number of metadata entries must match number of texts")
            metadata = request.metadata
            # Add text and timestamp to metadata
            for i, meta in enumerate(metadata):
                meta["text"] = request.texts[i]
                meta["timestamp"] = datetime.now().isoformat()
        
        # Create points
        points = [
            PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=meta
            )
            for point_id, embedding, meta in zip(point_ids, embeddings, metadata)
        ]
        
        # Get Qdrant client and store points
        qdrant_conn = QdrantConnection()
        logger.info(f"Storing {len(points)} points in collection '{request.collection_name}'")
        qdrant_conn.client.upsert(
            collection_name=request.collection_name,
            points=points
        )
        
        return EmbedResponse(
            success=True,
            message=f"Successfully embedded and stored {len(request.texts)} texts",
            ids=point_ids,
            count=len(request.texts)
        )
        
    except Exception as e:
        logger.error(f"Error in embed_and_store: {e}")
        raise HTTPException(status_code=500, detail=str(e))