import json

from fastapi import Header

from app.auth import verify_jwt
from app.config import settings
from app.db import get_db
from app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Any, Dict

### DBのオーバーライド
# テストでは一旦データベースをまっさらな状態にしテスト用のデータを投入する、ということを繰り返す
# そのため開発者のPCで動作している開発用のデータベースなどがぐちゃぐちゃになることを防ぐためテスト用の別のテーブルに接続させる

### ../conftest.py の @pytest.fixtureと混同しそうだが
## test/utils/overrides.pyでは
# テスト「される」側である、app/main.pyで定義されている各エンドポイントなどが利用するDB接続をオーバーライドしている
# app/main.pyで定義されている各エンドポイントはFastAPIライブラリのFastAPIクラスのメンバ関数であるFastAPI.get()などをデコレートしているので
# FastAPIクラスのインスタンスであるapp.main.appに対して、app.dependency_overrides[get_db] = override_get_db などとすることで、FastAPIライブラリが良しなにやってくれている
## 対して、test/conftest.pyでは
# テスト用テーブルが無ければ作成、各テストケース終了後のクリーンアップといった、「前処理・後処理」を担当している
# (必要であれば)加えて、テスト「する」側である、app/test/以下で定義されているテスト関数たちにテスト用DBへの接続を提供している
# (テストの前処理として、APIを経由せずデータベースに直接レコードを追加したかったりするので)
# これまたPytestモジュールのfixture関数をデコレートすることで実現している
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

### テストの時はJWTの検証をバイパス
# JWTのpayloadを「署名無し・(Base64エンコードではなく)JSON文字列形式」でAuthorizationヘッダーに指定する。
# 単にヘッダーで指定されたJSONをDictにして返す
def override_verify_jwt(authorization=Header(default=None))->Dict[str,Any]:
    return json.loads(authorization)
app.dependency_overrides[verify_jwt] = override_verify_jwt