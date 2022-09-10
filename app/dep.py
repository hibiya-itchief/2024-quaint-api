from datetime import datetime, timedelta
from typing import Union

from fastapi import Depends, FastAPI, HTTPException, status,Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from yarg import get
from sqlalchemy.orm.session import Session

from app import schemas
from app.config import settings

from .database import SessionLocal,engine
from . import crud

LOGIN_JWT_SECRET = settings.login_jwt_secret#HMAC 共有シークレットで署名。署名者だけが検証できれば良いなら128bit以上のSHA-256 Hashでいいぽい
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = settings.access_token_expire

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


pwd_context= CryptContext(schemes=["bcrypt"],deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/me/login")


def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(db:Session, username: str, password: str):
    user= crud.get_user_by_name(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, LOGIN_JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def login_for_access_token(username:str,password:str,db:Session):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名かパスワードが間違っています",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.password_expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="パスワードが失効しています。新しいパスワードを設定してください。",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=ACCESS_TOKEN_EXPIRE
    )
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(db:Session = Depends(get_db),token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="ログイン情報の有効性を確認できませんでした",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, LOGIN_JWT_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user:schemas.User = crud.get_user_by_name(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    if user.password_expired:
        raise HTTPException(401,detail="パスワードが失効しています。新しいパスワードを設定してください")
    return user

#例外を発生させないことで、ログインしてるならユーザー情報が取れるし、してないならNoneを返すようにする(顔出し画像が入る可能性があるカバー画像をレスポンスするか決める)
def get_current_user_not_exception(db:Session=Depends(get_db),Authorization:Union[str, None] = Header(default=None)):
    if Authorization is not None:
        token=Authorization.replace("Bearer ","")
    else:
        return None
    try:
        payload = jwt.decode(token, LOGIN_JWT_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = schemas.TokenData(username=username)
    except JWTError:
        return None
    user:schemas.User = crud.get_user_by_name(db, username=token_data.username)
    if user is None:
        return None
    if user.password_expired:
        return None
    return user


def admin(db:Session = Depends(get_db),user:schemas.User = Depends(get_current_user)):
    if not crud.check_admin(db,user):
        raise HTTPException(403,detail="Adminの権限がありません")
    return user

def entry(db:Session = Depends(get_db),user:schemas.User = Depends(get_current_user)):
    if not crud.check_entry(db,user):
        raise HTTPException(403,detail="Entryの権限がありません")
    return user

def owner_of(group_id:str,db:Session = Depends(get_db),user:schemas.User = Depends(get_current_user)):
    group=crud.get_group(db,group_id)###
    if not group:
        raise HTTPException(400,detail='Groupが見つかりません')
    if crud.check_admin(db,user):
        return user
    if not crud.check_owner_of(db,group,user):
        raise HTTPException(403,detail="Ownerの権限がありません")
    return user

def owner(db:Session = Depends(get_db),user:schemas.User = Depends(get_current_user)):
    if crud.check_admin(db,user):
        return user
    if not crud.check_owner(db,user):
        raise HTTPException(403,detail="Ownerの権限がありません")
    return user

def authorizer_of(group_id:str,db:Session = Depends(get_db),user:schemas.User=Depends(get_current_user)):
    group=crud.get_group(db,group_id)###
    if not group:
        raise HTTPException(400,detail='Groupが見つかりません')
    if crud.check_admin(db,user):
        return user
    if crud.check_owner_of(db,group,user):
        return user
    if not crud.check_authorizer_of(db,group,user):
        raise HTTPException(403,detail="Authorizerの権限がありません")
    return user

def authorizer(db:Session = Depends(get_db),user:schemas.User=Depends(get_current_user)):
    if crud.check_admin(db,user):
        return user
    if crud.check_owner(db,user):
        return user
    if not crud.check_authorizer(db,user):
        raise HTTPException(403,detail="Authorizerの権限がありません")
    return user
