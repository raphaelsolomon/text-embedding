from datetime import datetime
from typing import Optional
from config.logger import get_logger
from database.app import MongoDBConnection
from fastapi import HTTPException

logger = get_logger(__name__)

async def get_articles(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    first: int = 100,
    page: int = 1
):
    """
    Fetch articles from MongoDB based on created_at or published_date
    
    Query parameters:
    - start_date: Optional ISO format date string (YYYY-MM-DD)
    - end_date: Optional ISO format date string (YYYY-MM-DD)
    - first: Maximum number of articles to return per page (default: 100)
    - page: Page number to fetch (default: 1)
    """
    
    db = MongoDBConnection().db
    
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB service not ready")
    
    try:
        # Ensure page is at least 1
        if page < 1:
            page = 1
            
        # Calculate skip value from page and first
        skip = (page - 1) * first
        
        # Build the query
        query = {}
        
        if start_date or end_date:
            date_query = {}
            
            # Convert string dates to datetime objects
            if start_date:
                try:
                    start_datetime = datetime.fromisoformat(start_date)
                    date_query["$gte"] = start_datetime
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
            
            if end_date:
                try:
                    end_datetime = datetime.fromisoformat(end_date)
                    # Set to end of day
                    end_datetime = end_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
                    date_query["$lte"] = end_datetime
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
            
            # Apply date query to both fields
            query["$or"] = [
                {"created_at": date_query},
                {"published_date": date_query}
            ]
            
            query["content"] = {"$ne": ""}  # Ensure content is not empty
        
        logger.info(f"Fetching articles with query: {query}, first: {first}, page: {page}")
        
        # Execute the query
        articles_cursor = db['n8n'].find(query).skip(skip).limit(first)
        total_count = db['n8n'].count_documents(query)
        
        articles = []
        for doc in articles_cursor:
            # Convert ObjectId to string for JSON serialization
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
                
            # Format dates to ISO strings for consistent output
            if "created_at" in doc and isinstance(doc["created_at"], datetime):
                doc["created_at"] = doc["created_at"].isoformat()
                
            if "published_date" in doc and isinstance(doc["published_date"], datetime):
                doc["published_date"] = doc["published_date"].isoformat()
                
            articles.append(doc)
        
        # Calculate pagination metadata
        total_pages = (total_count + first - 1) // first if first > 0 else 0
        
        return {
            "total_count": total_count,
            "first": first,
            "page": page,
            "total_pages": total_pages,
            "articles": articles,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")