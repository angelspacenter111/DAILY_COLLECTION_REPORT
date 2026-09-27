import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URI, DATABASE_NAME

# Ensure certifi CA bundle is used for SSL/TLS verification
ca_file = certifi.where()

# Asynchronous MongoDB client for FastAPI operations
# Optimized for cloud servers, serverless (Lambda/Vercel/ECS), and local environments
async_client = AsyncIOMotorClient(
    MONGODB_URI,
    tlsCAFile=ca_file,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000,
    maxPoolSize=50,
    minPoolSize=0,            # Must be 0 in cloud/serverless so idle connections are not forcefully held
    maxIdleTimeMS=30000,      # Recycle idle sockets before cloud NAT/Atlas drops them (prevents connection closed)
    retryWrites=True,          # Automatically retry transient write failures
    retryReads=True           # Automatically retry transient read failures
)
db = async_client[DATABASE_NAME]

# Lazy synchronous client (only initialized if explicitly called, preventing background monitoring threads on import)
_sync_client = None

def get_sync_db():
    global _sync_client
    if _sync_client is None:
        from pymongo import MongoClient
        _sync_client = MongoClient(
            MONGODB_URI,
            tlsCAFile=ca_file,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
            maxPoolSize=10,
            minPoolSize=0,
            maxIdleTimeMS=30000,
            retryWrites=True,
            retryReads=True,
            connect=False
        )
    return _sync_client[DATABASE_NAME]

class _LazySyncDb:
    def __getattr__(self, name):
        return getattr(get_sync_db(), name)

    def __getitem__(self, name):
        return get_sync_db()[name]

sync_db = _LazySyncDb()
sync_client = None