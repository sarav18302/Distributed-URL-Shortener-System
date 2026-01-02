from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from typing import List, Optional, Dict, Any
import hashlib
import time
from datetime import datetime, timezone, timedelta
from collections import OrderedDict
import asyncio
from functools import lru_cache

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("CORS middleware configured to allow http://localhost:3000")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============ LRU CACHE IMPLEMENTATION ============
class LRUCache:
    """In-memory LRU cache for hot URLs with O(1) operations"""
    def __init__(self, capacity: int = 1000):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[str]:
        if key not in self.cache:
            self.misses += 1
            return None
        self.cache.move_to_end(key)
        self.hits += 1
        return self.cache[key]
    
    def put(self, key: str, value: str) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def invalidate(self, key: str) -> None:
        if key in self.cache:
            del self.cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2)
        }

# Global cache instance
url_cache = LRUCache(capacity=1000)


# ============ RATE LIMITER ============
class RateLimiter:
    """Token bucket rate limiter for API protection"""
    def __init__(self, rate: int = 10, per: int = 60):
        self.rate = rate
        self.per = per
        self.allowance = {}
        self.last_check = {}
    
    async def is_allowed(self, identifier: str) -> bool:
        current = time.time()
        
        if identifier not in self.allowance:
            self.allowance[identifier] = self.rate
            self.last_check[identifier] = current
            return True
        
        time_passed = current - self.last_check[identifier]
        self.last_check[identifier] = current
        self.allowance[identifier] += time_passed * (self.rate / self.per)
        
        if self.allowance[identifier] > self.rate:
            self.allowance[identifier] = self.rate
        
        if self.allowance[identifier] < 1.0:
            return False
        
        self.allowance[identifier] -= 1.0
        return True

rate_limiter = RateLimiter(rate=100, per=60)


# ============ BASE62 ENCODING ============
BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def encode_base62(num: int) -> str:
    """Convert number to base62 string"""
    if num == 0:
        return BASE62[0]
    
    result = []
    while num:
        num, remainder = divmod(num, 62)
        result.append(BASE62[remainder])
    
    return ''.join(reversed(result))

def generate_short_code(url: str, counter: int = 0) -> str:
    """Generate short code using hash + counter for collision handling"""
    hash_input = f"{url}{counter}".encode('utf-8')
    hash_value = int(hashlib.sha256(hash_input).hexdigest(), 16)
    short_code = encode_base62(hash_value)[:7]
    return short_code


# ============ PYDANTIC MODELS ============
class URLCreate(BaseModel):
    url: str
    custom_alias: Optional[str] = None

class URLResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    short_code: str
    original_url: str
    created_at: datetime
    clicks: int = 0
    custom_alias: Optional[str] = None

class URLStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    short_code: str
    original_url: str
    clicks: int
    created_at: datetime
    last_accessed: Optional[datetime] = None
    click_history: List[Dict[str, Any]] = []

class ClickEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    short_code: str
    timestamp: datetime
    user_agent: Optional[str] = None
    referer: Optional[str] = None

class SystemMetrics(BaseModel):
    total_urls: int
    total_clicks: int
    cache_stats: Dict[str, Any]
    top_urls: List[Dict[str, Any]]
    recent_clicks: int


# ============ HELPER FUNCTIONS ============
async def get_next_counter() -> int:
    """Get next counter value for collision handling"""
    result = await db.counters.find_one_and_update(
        {"_id": "url_counter"},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True
    )
    return result["value"] if result else 0

async def record_click(short_code: str, request: Request):
    """Record click event for analytics"""
    click_event = {
        "short_code": short_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_agent": request.headers.get("user-agent"),
        "referer": request.headers.get("referer")
    }
    
    await db.clicks.insert_one(click_event)
    await db.urls.update_one(
        {"short_code": short_code},
        {
            "$inc": {"clicks": 1},
            "$set": {"last_accessed": datetime.now(timezone.utc).isoformat()}
        }
    )


# ============ API ENDPOINTS ============
@api_router.get("/")
async def root():
    return {
        "service": "Distributed URL Shortener",
        "version": "1.0.0",
        "features": [
            "LRU Caching",
            "Rate Limiting",
            "Analytics",
            "Custom Aliases"
        ]
    }

@api_router.post("/shorten", response_model=URLResponse)
async def shorten_url(url_data: URLCreate, request: Request):
    """Shorten a URL with collision handling and caching"""
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not await rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Validate URL format
    url = url_data.url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Check if URL already exists
    existing = await db.urls.find_one({"original_url": url}, {"_id": 0})
    if existing:
        if isinstance(existing['created_at'], str):
            existing['created_at'] = datetime.fromisoformat(existing['created_at'])
        return URLResponse(**existing)
    
    # Handle custom alias
    if url_data.custom_alias:
        alias_exists = await db.urls.find_one({"short_code": url_data.custom_alias})
        if alias_exists:
            raise HTTPException(status_code=400, detail="Custom alias already taken")
        short_code = url_data.custom_alias
    else:
        # Generate short code with collision handling
        counter = 0
        while True:
            short_code = generate_short_code(url, counter)
            exists = await db.urls.find_one({"short_code": short_code})
            if not exists:
                break
            counter = await get_next_counter()
    
    # Create URL document
    url_doc = {
        "short_code": short_code,
        "original_url": url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "clicks": 0,
        "custom_alias": url_data.custom_alias
    }
    
    await db.urls.insert_one(url_doc)
    
    # Cache warming
    url_cache.put(short_code, url)
    
    url_doc['created_at'] = datetime.fromisoformat(url_doc['created_at'])
    return URLResponse(**url_doc)

@api_router.get("/expand/{short_code}")
async def expand_url(short_code: str, request: Request):
    """Redirect to original URL with caching and analytics"""
    start_time = time.time()
    
    # Check cache first (read-through pattern)
    cached_url = url_cache.get(short_code)
    
    if cached_url:
        # Cache hit
        asyncio.create_task(record_click(short_code, request))
        logger.info(f"Cache HIT for {short_code} - Latency: {(time.time() - start_time) * 1000:.2f}ms")
        return RedirectResponse(url=cached_url, status_code=302)
    
    # Cache miss - query database
    url_doc = await db.urls.find_one({"short_code": short_code}, {"_id": 0})
    
    if not url_doc:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    original_url = url_doc["original_url"]
    
    # Write-through cache
    url_cache.put(short_code, original_url)
    
    # Record analytics asynchronously
    asyncio.create_task(record_click(short_code, request))
    
    logger.info(f"Cache MISS for {short_code} - Latency: {(time.time() - start_time) * 1000:.2f}ms")
    return RedirectResponse(url=original_url, status_code=302)

@api_router.get("/stats/{short_code}", response_model=URLStats)
async def get_url_stats(short_code: str):
    """Get detailed statistics for a short URL"""
    url_doc = await db.urls.find_one({"short_code": short_code}, {"_id": 0})
    
    if not url_doc:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    # Get click history
    clicks = await db.clicks.find(
        {"short_code": short_code},
        {"_id": 0}
    ).sort("timestamp", -1).limit(50).to_list(50)
    
    url_doc['click_history'] = clicks
    
    # Convert timestamps
    if isinstance(url_doc['created_at'], str):
        url_doc['created_at'] = datetime.fromisoformat(url_doc['created_at'])
    if url_doc.get('last_accessed') and isinstance(url_doc['last_accessed'], str):
        url_doc['last_accessed'] = datetime.fromisoformat(url_doc['last_accessed'])
    
    return URLStats(**url_doc)

@api_router.get("/urls", response_model=List[URLResponse])
async def list_urls(limit: int = 100):
    """List all shortened URLs"""
    urls = await db.urls.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    for url in urls:
        if isinstance(url['created_at'], str):
            url['created_at'] = datetime.fromisoformat(url['created_at'])
    
    return urls

@api_router.delete("/urls/{short_code}")
async def delete_url(short_code: str):
    """Delete a short URL and invalidate cache"""
    result = await db.urls.delete_one({"short_code": short_code})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    # Cache invalidation
    url_cache.invalidate(short_code)
    
    # Clean up click history
    await db.clicks.delete_many({"short_code": short_code})
    
    return {"message": "URL deleted successfully"}

@api_router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics():
    """Get system-wide metrics and analytics"""
    total_urls = await db.urls.count_documents({})
    
    # Aggregate total clicks
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$clicks"}}}
    ]
    click_result = await db.urls.aggregate(pipeline).to_list(1)
    total_clicks = click_result[0]["total"] if click_result else 0
    
    # Top URLs by clicks
    top_urls = await db.urls.find(
        {}, 
        {"_id": 0, "short_code": 1, "original_url": 1, "clicks": 1}
    ).sort("clicks", -1).limit(10).to_list(10)
    
    # Recent clicks (last hour)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_clicks = await db.clicks.count_documents({
        "timestamp": {"$gte": one_hour_ago.isoformat()}
    })
    
    return SystemMetrics(
        total_urls=total_urls,
        total_clicks=total_clicks,
        cache_stats=url_cache.get_stats(),
        top_urls=top_urls,
        recent_clicks=recent_clicks
    )

@api_router.post("/cache/clear")
async def clear_cache():
    """Clear the entire cache (admin operation)"""
    url_cache.cache.clear()
    url_cache.hits = 0
    url_cache.misses = 0
    return {"message": "Cache cleared successfully"}


# Include the router in the main app
app.include_router(api_router)



@app.on_event("startup")
async def startup_db():
    """Create indexes for optimal query performance"""
    # Compound index for fast lookups
    await db.urls.create_index("short_code", unique=True)
    await db.urls.create_index("original_url")
    await db.urls.create_index([("clicks", -1)])
    
    # TTL index for clicks (optional: expire old click data after 90 days)
    await db.clicks.create_index("timestamp")
    await db.clicks.create_index("short_code")
    
    logger.info("Database indexes created successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()