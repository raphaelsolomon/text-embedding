import os
from config.handler import get_yesterday_today_range
from config.logger import get_logger
from controllers.trending import get_trending_articles_by_date
import requests
from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook-test/3c6b4e8b-b2d4-434b-ae4b-39c8eca89c43")

async def background_task():
    try:
        date_range = get_yesterday_today_range()
        logger.info(f"Running background task with date range: {date_range}")

        start_date = date_range['start_date'].isoformat()
        end_date = date_range['end_date'].isoformat()

        trending_articles = await get_trending_articles_by_date(
            start_date=start_date,
            end_date=end_date, 
            first=150, 
            page=1
        )

        response = requests.post(
            url=N8N_WEBHOOK_URL,
            json={"articles": trending_articles},
            timeout=30
        )

        response.raise_for_status()
        logger.info(f"Successfully sent trending articles to n8n: {response.status_code}")
        parsed = response.json()
        logger.info(f"n8n response: {parsed}")

    except requests.RequestException as e:
        logger.error(f"Failed to send trending articles to n8n: {e}")
    except Exception as e:
        logger.error(f"Error in background task: {e}")

