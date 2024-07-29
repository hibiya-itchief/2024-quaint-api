from fastapi.testclient import TestClient
from app.main import app
from app.auth import verify_jwt
from app.test.utils.overrides import override_verify_jwt

client=TestClient(app)

### test/overrides.pyによってバイパスしてしまっているapp.auth.verify_jwt()自体のテストをする
# EntraIDから正しいトークンを自動で取得して成功することを確認するテストは難しくても、間違ったトークンではしっかり失敗することだけでもテストしたい

# verify_jwt()に依存しているエンドポイントの例として、"/users/me/tickets"を使っている
# このやり方がベストなのかわからない。本当は関数単体でテスト出来るといいんだけど
def test_verify_jwt_fail():
    app.dependency_overrides[verify_jwt]=verify_jwt # test/overrides.pyでoverrideした依存関係を元に戻す
    response=client.get("/users/me/tickets",headers={'Authorization':"Bearer invalid.jwt.token"}) # もっといろんなパターンのinvalidなトークン(payloadはvalidだがsignatureがinvalid,有効期限だけinvalid...など)を試すべき？
    assert response.status_code==401
    app.dependency_overrides[verify_jwt]=override_verify_jwt # 再びoverride

