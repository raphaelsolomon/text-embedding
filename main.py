import sys
import signal
import threading
from config.models import app
from config.models.app import CollectionRequest, EmbedRequest, EmbedResponse
from database.app import MongoDBConnection
from controllers.collection import create_qdrant_collection
from controllers.embed import embed_and_store_to_qdrant
from controllers.trending import get_trending_articles_by_date
from controllers.articles import get_articles
from qdrant.app import QdrantConnection
from scheduler.app import setup_scheduler
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
from typing import Optional
import os
from dotenv import load_dotenv
import asyncio
from config.logger import get_logger


# Configure logging
logger = get_logger(__name__)

app = FastAPI(title="Qdrant Embedding API", version="1.0.0")

# Global variables
model = None
qdrant_client = None
shutdown_flag = False

# Configuration from environment variables
QDRANT_HOST = os.getenv("QDRANT_HOST", "51.222.28.24")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "a71d9f9b-8d34-41be-a7c8-4f0d5b12c6e3")
VECTOR_SIZE = 384  # all-mpnet-base-v2 embedding size

# Startup Event
@app.on_event("startup")
async def startup_event():
    global model, qdrant_client
    
    try:
        # Load sentence transformer model
        logger.info("Loading sentence transformer model...")
        model = SentenceTransformer('all-mpnet-base-v2')
        logger.info("Model loaded successfully!")
        
        # Initialize Qdrant connection
        logger.info("Initializing Qdrant connection")
        qdrant_conn = QdrantConnection()
        # Test the connection
        collections = qdrant_conn.client.get_collections()
        logger.info(f"Qdrant connection successful! Found {len(collections.collections)} collections")

        # Add MongoDB connection
        logger.info(f"Connecting to MongoDB")
        mongo_conn = MongoDBConnection()
        # Use the client property to access the admin database and run the ping command
        mongo_conn.client.admin.command('ping')
        logger.info("MongoDB connection successful!")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise e

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Qdrant Embedding API is running"}

@app.post("/collections")
async def create_collection(request: CollectionRequest):
   return await create_qdrant_collection(request)

@app.post("/embed", response_model=EmbedResponse)
async def embed_and_store(request: EmbedRequest):
    return await embed_and_store_to_qdrant(request, model)

@app.get("/all-articles")
async def get_all_articles(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    first: int = 100,
    page: int = 1
):
   return await get_articles(start_date, end_date, first, page)

@app.get("/trending-articles")
async def get_trending_articles(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    first: int = 100,
    page: int = 1
):
    return await get_trending_articles_by_date(start_date, end_date, first, page)

def start_api_server():
    """Start the FastAPI server"""
    import uvicorn
    logger.info("Starting API server")
    uvicorn.run(app, host="0.0.0.0", port=8009)

def signal_handler(sig, frame):
    """Handle system signals for graceful shutdown"""
    global shutdown_flag
    logger.info(f"Received shutdown signal {sig}")
    shutdown_flag = True

async def main():
    """Main function to run the server"""
    try:
        # Load environment variables
        load_dotenv()
        logger.info("Starting Switchwise application")
        
        # Initialize database connection
        try:
            db_conn = MongoDBConnection()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            logger.warning("Continuing without database connection")

        try:
            scheduler = await setup_scheduler()
            scheduler.start()
            logger.info("Task scheduler started")
        except Exception as e:
            logger.error(f"Failed to set up scheduler: {str(e)}")
            sys.exit(1)

        # Start API server in a separate thread
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        logger.info("API server thread started")

        # Register signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, signal_handler)

        # Main application loop
        logger.info("Application running. Press Ctrl+C to exit.")
        logger.info("GraphQL API available at http://localhost:8000/graphql")
        while not shutdown_flag:
            await asyncio.sleep(1)
            
        # Perform shutdown tasks
        logger.info("Performing graceful shutdown")
        scheduler.stop()
        try:
            if 'db_conn' in locals():
                db_conn.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")

        logger.info("Shutdown complete")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())