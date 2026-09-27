from sqlalchemy import create_engine

DATABASE_URL = "mysql+pymysql://root:@localhost:3306/fastapi_practice"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)