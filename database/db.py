import os 
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# all env variables load using this 
load_dotenv()

# retrieve database_url from .env
SQLACHEMY_DATABASE_URL = os.getenv('DATABASE_URL')

# SQLite connection setup
engine = create_engine(
    SQLACHEMY_DATABASE_URL , connect_args={"check_same_thread":False}
)

sessionLocal = sessionmaker(autocommit=False , autoflush=False , bind=engine)

Base = declarative_base()

# DB session
def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()