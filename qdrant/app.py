"""
Qdrant vector database connection setup module
"""
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from dotenv import load_dotenv
from config.logger import get_logger

logger = get_logger(__name__)

class QdrantConnection:
    """
    Qdrant connection class to handle vector database operations
    Implements singleton pattern for reuse throughout the application
    """
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QdrantConnection, cls).__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        """Connect to Qdrant using environment variables"""
        try:
            load_dotenv()
            
            # Configuration from environment variables
            qdrant_host = os.getenv("QDRANT_HOST", "localhost")
            qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
            qdrant_api_key = os.getenv("QDRANT_API_KEY", "r0grgy4ere-8d34-41be-a7c8-4f0d5b12c6e3")
            
            logger.info(f"Connecting to Qdrant at {qdrant_host}:{qdrant_port}")
            
            self._client = QdrantClient(
                host=qdrant_host,
                port=qdrant_port,
                api_key=qdrant_api_key,
                https=False,
                timeout=30
            )
            
            # Verify connection by getting collections
            collections = self._client.get_collections()
            logger.info(f"Qdrant connection successful! Found {len(collections.collections)} collections")
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            self._client = None
            raise

    @property
    def client(self) -> QdrantClient:
        """Get Qdrant client instance"""
        if self._client is None:
            self._connect()
        return self._client
    
    def create_collection(self, collection_name, vector_size=384, distance="Cosine"):
        """
        Create a new collection in Qdrant
        
        Args:
            collection_name (str): Name of the collection to create
            vector_size (int): Size of the vectors to store
            distance (str): Distance metric to use (Cosine, Euclidean, Dot)
            
        Returns:
            dict: Information about the created collection
        """
        try:
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclidean": Distance.EUCLID,
                "Dot": Distance.DOT
            }
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_map.get(distance, Distance.COSINE)
                )
            )
            
            return {
                "success": True,
                "message": f"Collection '{collection_name}' created successfully",
                "collection_name": collection_name,
                "vector_size": vector_size,
                "distance": distance
            }
            
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise
            
    def close(self):
        """Close Qdrant connection"""
        if self._client is not None:
            # Qdrant client doesn't have an explicit close method, but we can set it to None
            logger.info("Closing Qdrant connection")
            self._client = None