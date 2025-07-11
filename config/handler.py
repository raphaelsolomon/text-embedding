
import math
from typing import List
from urllib.parse import urlparse
from dotenv import load_dotenv
from config.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

def get_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except:
        return ""
    
def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a ** 2 for a in vec1))
    norm_b = math.sqrt(sum(b ** 2 for b in vec2))
    return dot_product / (norm_a * norm_b) if norm_a and norm_b else 0.0

