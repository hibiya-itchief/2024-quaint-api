from typing import Generator

import pytest
from app.config import settings
from app.db import Base
from app.main import app
from app.test.utils.overrides import TestingSessionLocal, engine
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy_utils import create_database, database_exists

TEST_DATABASE_URI = "mysql://"+ settings.mysql_user +":"+ settings.mysql_password +"@"+ settings.db_host +"/quaint-app-test"

### データベースのfixture
# 各テストケースが実行されるごとに、データベースを他のテストの影響を受けない(=全て削除された)クリーンな状態にしたうえで、DBへの接続を提供する

### ./utils/overrides.pyの app.dependency_overrides[get_db] = override_get_db と混同しそうだが
## test/conftest.pyでは
# テスト用テーブルが無ければ作成、各テストケース終了後のクリーンアップといった、「前処理・後処理」を担当している
# (必要であれば)加えて、テスト「する」側である、app/test/以下で定義されているテスト関数たちにテスト用DBへの接続を提供している
# (テストの前処理として、APIを経由せずデータベースに直接レコードを追加したかったりするので)
# Pytestモジュールのfixture関数をデコレートすることで実現している
## 対してtest/utils/overrides.pyでは
# テスト「される」側である、app/main.pyで定義されている各エンドポイントなどが利用するDB接続をオーバーライドしている
# app/main.pyで定義されている各エンドポイントはFastAPIライブラリのFastAPIクラスのメンバ関数であるFastAPI.get()などをデコレートしているので
# FastAPIクラスのインスタンスであるapp.main.appに対して、app.dependency_overrides[get_db] = override_get_db などとすることで、FastAPIライブラリが良しなにやってくれている

@pytest.fixture(scope="function",autouse=True)
def db() -> Generator[Session, None, None]:
    if not database_exists(TEST_DATABASE_URI):
        create_database(TEST_DATABASE_URI)

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
