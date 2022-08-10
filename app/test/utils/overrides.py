import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.main import app
from app.dep import get_db

TEST_DATABASE_URI = "mysql://"+ settings.mysql_user +":"+ settings.mysql_password +"@"+ settings.db_host +"/quaint-app-test"

engine = create_engine(TEST_DATABASE_URI)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db