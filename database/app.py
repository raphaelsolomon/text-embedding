"""
MongoDB database connection setup module
"""
import os
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv
from config.logger import get_logger

logger = get_logger(__name__)

class MongoDBConnection:
    """
    MongoDB connection class to handle database operations
    """
    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        """Connect to MongoDB using environment variables"""
        try:
            load_dotenv()
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
            logger.info(f"Connecting to MongoDB at {mongo_uri}")
            db_name = os.getenv("MONGO_DB", "n8n")
            
            logger.info(f"Connecting to MongoDB at {mongo_uri}")
            self._client = MongoClient(mongo_uri)
            self._db = self._client[db_name]
            logger.info(f"Successfully connected to MongoDB database: {db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    @property
    def db(self) -> Database:
        """Get database instance"""
        # Don't check with `if not self._db` as that would cause the error
        # Instead check for None explicitly
        if self._db is None:
            self._connect()
        return self._db
        
    @property
    def client(self) -> MongoClient:
        """Get MongoDB client instance"""
        if self._client is None:
            self._connect()
        return self._client

    def close(self):
        """Close MongoDB connection"""
        if self._client is not None:
            self._client.close()
            logger.info("MongoDB connection closed")
            # Reset the client and DB references
            self._client = None
            self._db = None