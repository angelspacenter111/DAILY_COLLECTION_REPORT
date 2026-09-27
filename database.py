import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from config import MONGODB_URI, DATABASE_NAME

# Asynchronous MongoDB client for FastAPI operations
async_client = AsyncIOMotorClient(
    MONGODB_URI,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    maxPoolSize=50,
    minPoolSize=5,
    maxIdleTimeMS=45000
)
db = async_client[DATABASE_NAME]

# Synchronous MongoDB client for scripts and testing
sync_client = MongoClient(
    MONGODB_URI,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    maxPoolSize=20,
    maxIdleTimeMS=45000
)
sync_db = sync_client[DATABASE_NAME]