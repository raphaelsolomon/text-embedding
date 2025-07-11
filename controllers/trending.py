from datetime import datetime
from typing import Optional
from config.logger import get_logger
from database.app import MongoDBConnection
from config.handler import cosine_similarity, get_domain
from config.models.app import CompareItem
from qdrant.app import QdrantConnection
from fastapi import HTTPException

logger = get_logger(__name__)

async def get_trending_articles_by_date(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    first: int = 100,
    page: int = 1,
):
    """
    Fetch articles from MongoDB based on created_at or published_date
    
    Query parameters:
    - start_date: Optional ISO format date string (YYYY-MM-DD)
    - end_date: Optional ISO format date string (YYYY-MM-DD)
    """
    
    qdrant_conn = QdrantConnection()
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
            
            query["embedding_id"] = {"$exists": True, "$ne": None}  # Ensure embedding_id exists
            query["content"] = {"$ne": ""}  # Ensure content is not empty
        
        logger.info(f"Fetching articles with query: {query}")
        
        # Execute the query
        articles_cursor = db['n8n'].find(query).sort("created_at", -1).skip(skip).limit(first)
        
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

        # Process each article
        results = []
        logger.info("Starting comparison of articles...")
        for i, reference_article in enumerate(articles):
            # Get domain of reference article
            reference_domain = get_domain(reference_article.get('url'))
            
            # Filter out articles from the same domain
            filtered_articles = []
            for other_article in articles:
                # Skip the reference article itself
                if other_article['embedding_id'] == reference_article['embedding_id']:
                    continue
                
                # Skip articles from the same domain
                other_domain = get_domain(other_article['url'])
                if other_domain == reference_domain:
                    continue
                
                # Add to filtered list
                filtered_articles.append(other_article)
            
            # Create compare item
            compare_item = CompareItem(
                referenceId=reference_article['embedding_id'],
                url=reference_article['url'],
                title=reference_article['title'],
                filtered_articles=filtered_articles
            )
            
            results.append(compare_item)


        trending_articles = []
        for i, compare_item in enumerate(results):
            try:
                parsed_id = int(compare_item.referenceId)
            except ValueError:
                parsed_id = compare_item.referenceId

            points = qdrant_conn.client.retrieve(
                collection_name="documents",
                ids=[parsed_id],
                with_payload=True,
                with_vectors=True
            )

            if not points:
                raise HTTPException(
                    status_code=404,
                    detail=f"Point with ID {parsed_id} not found in collection documents"
                )
            
            point = points[0]
            reference_vector = point.vector

            other_articles = compare_item.filtered_articles
            similar_articles = []
            for other_article in other_articles:
                try:
                    parsed_id = int(other_article.embedding_id)
                except ValueError:
                    parsed_id = other_article.embedding_id

                other_points = qdrant_conn.client.retrieve(
                    collection_name="documents",
                    ids=[parsed_id],
                    with_payload=True,
                    with_vectors=True
                )

                if not other_points:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Point with ID {parsed_id} not found in collection documents"
                    )
                
                other_point = other_points[0]
                other_vector = other_point.vector

                # Calculate cosine similarity
                similarity = cosine_similarity(reference_vector, other_vector)
                logger.info(f"Similarity between {compare_item.referenceId} and {other_article.embedding_id}: {similarity}")

                if similarity >= 0.78:
                    similar_articles.append({
                        "embedding_id": other_article.embedding_id,
                        "similarity": similarity
                    })

            if len(similar_articles) > 0:
                trending_articles.append({
                    "referenceId": compare_item.referenceId,
                    "url": compare_item.url,
                    "title": compare_item.title,
                    "similar_articles": similar_articles
                })

        return trending_articles
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")