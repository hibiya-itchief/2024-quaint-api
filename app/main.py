import json
import time
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Union
from xml.dom.minidom import Entity

import requests
from io import StringIO
import pandas as pd
from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import Field
from sqlalchemy.orm import Session
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from app import auth, crud, db, models, schemas, blob_storage
from app.config import settings
from app.ga import ga_screenpageview
from app.msgraph import MsGraph
from app.redis_possible import redis_get_if_possible, redis_set_if_possible

# models.Base.metadata.create_all(bind=engine)

description = """
日比谷高校オンライン整理券システム「QUAINT」のAPI \n
<a href="https://seiryofes.com">seiryofes.com</a>
<a href="https://github.com/hibiya-itchief/quaint-api">GitHub</a> \n \n
"""
if settings.production_flag == 1:
    description += "<h2>本番環境</h2>"
description += settings.api_hostname

tags_metadata = [
    {
        "name": "users",
        "description": "ユーザー",
    },
    {"name": "groups", "description": "Group : 星陵祭に参加する各団体"},
    {"name": "events", "description": "Event : 各参加団体がもつ公演"},
    {"name": "tickets", "description": "Ticket : 各公演に入場するための整理券"},
    {"name": "votes", "description": "Vote : 生徒による1、2年クラス劇投票"},
    {"name": "tags", "description": "Tag : Groupにひもづけられるタグ"},
    {"name": "admin", "description": "管理者用API"},
    {"name": "chief", "description": "チーフ会用API"},
    {"name": "ga", "description": "Google Analytics"},
]

app = FastAPI(
    title="QUAINT-API",
    description=description,
    openapi_tags=tags_metadata,
    version="0.1.0",
)
### TODO 同一オリジンにアップロードしてcorsは許可しない
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_CACHE_EXPIRE = 120  # (何か特別な意図があってRedisを使うわけでは無く)DB負荷軽減のためにRedisキャッシュするエンドポイントのexpire


@app.get("/")
def read_root():
    return {
        "title": "QUAINT-API",
        "description": "日比谷高校オンライン整理券システム「QUAINT」のAPI",
    }


@app.get(
    "/users/me/tickets",
    response_model=List[schemas.Ticket],
    summary="ログイン中のユーザーが所有している整理券のリストを取得",
    tags=["users"],
    description="### 必要な権限\nなし\n### ログインが必要か\nはい\n###注意 \n状態がcancelledになっているチケットも含めて返ってくる",
)
def get_list_of_your_tickets(
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    return crud.get_list_of_your_tickets(db, user)


@app.get(
    "/users/me/tickets/active",
    response_model=List[schemas.Ticket],
    summary="ログイン中のユーザーが所有しているactive状態のチケットを取得",
    tags=["users"],
    description="### 必要な権限\nなし\n### ログインが必要か\nはい\n###注意 \n状態がactiveになっているチケットを返す",
)
def get_list_of_your_tickets_active(
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    return crud.get_list_of_your_tickets_active(db, user)


@app.get(
    "/users/me/family/belong/{group_id}",
    response_model=bool,
    summary="保護者が指定された団体の保護者として登録されているか",
    tags=["users"],
    description="### 必要な権限\n保護者\n### ログインが必要か\nはい",
)
def get_is_parent_belong_to(
    group_id: str, user: schemas.JWTUser = Depends(auth.get_current_user)
):
    if not auth.check_parents(user):
        raise HTTPException(403, "保護者である必要があります。")
    return crud.is_parent_belong_to(group_id, user)


@app.get(
    "/users/me/tickets/family",
    response_model=bool,
    summary="保護者がすでに優先券を使い切っているか",
    tags=["users"],
    description="### 必要な権限\n保護者\n### ログインが必要か\nはい",
)
def is_buy_all_family_ticket(
    user: schemas.JWTUser = Depends(auth.parents), db: Session = Depends(db.get_db)
):
    if crud.count_taken_family_ticket(db, user) >= 2:
        return True
    return False


@app.get(
    "/users/me/count/tickets/family",
    response_model=int,
    summary="保護者が取得済みの優先券の数を返す",
    tags=["users"],
    description="### 必要な権限\n保護者\n### ログインが必要か\nはい",
)
def count_taken_family_tickets(
    user: schemas.JWTUser = Depends(auth.parents), db: Session = Depends(db.get_db)
):
    return crud.count_taken_family_ticket(db, user)


@app.put(
    "/users/{user_sub}/visit",
    summary="ユーザーの入校処理",
    tags=["users"],
    description="### 必要な権限\nEntry\n### ログインが必要か\nはい\n",
)
def activate_user(
    user_sub: str,
    permission: schemas.JWTUser = Depends(auth.entry),
    db: Session = Depends(db.get_db),
):
    msgraph = MsGraph()
    result = msgraph.change_jobTitle(user_sub, jobTitle="Visited")
    if result.status_code == 204:
        return {"OK": True}
    raise HTTPException(result.status_code, result.text)


@app.get(
    "/users/me/owner_of",
    response_model=List[str],
    summary="ownerが自分が権限のある団体を確認する",
    tags=["users"],
    description="### 必要な権限\nowner\n### ログインが必要か\nはい\n",
)
def check_ownership_of_user(
    user: schemas.JWTUser = Depends(auth.owner), db: Session = Depends(db.get_db)
):
    return crud.get_ownership_of_user(db, user.oid)


@app.get(
    "/users/{user_oid}/owner_of",
    response_model=List[str],
    summary="ユーザーの権限のある団体を確認する",
    tags=["users"],
    description="### 必要な権限\nadmin\n### ログインが必要か\nはい\n",
)
def check_ownership_of_user(
    user_oid: str,
    permission: schemas.JWTUser = Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    return crud.get_ownership_of_user(db, user_oid)


@app.get(
    "/users/owner_of",
    response_model=List[schemas.GroupOwner],
    summary="団体代表者のユーザーと団体の紐づけを全て確認する",
    tags=["users"],
    description="### 必要な権限\nadmin\n### ログインが必要か\nはい\n",
)
def check_all_ownership(
    permission: schemas.JWTUser = Depends(auth.admin), db: Session = Depends(db.get_db)
):
    return crud.get_all_ownership(db)


@app.put(
    "/users/{user_oid}/owner_of",
    response_model=schemas.GroupOwner,
    summary="団体代表者のユーザーとGroupを紐づける",
    tags=["users"],
    description="### 必要な権限\nadmin\n### ログインが必要か\nはい\n",
)
def grant_ownership(
    user_oid: str,
    group_id: str,
    note: Union[str, None],
    permission=Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    group = crud.get_group_public(db, group_id)
    if not group:
        raise HTTPException(404, "グループが見つかりません")
    return crud.grant_ownership(db, group, user_oid, note)


@app.delete(
    "/users/{user_oid}/owner_of",
    summary="団体代表者のユーザーとGroupの紐づけを削除",
    tags=["users"],
    description="### 必要な権限\nadmin\n### ログインが必要か\nはい\n",
)
def delete_ownership(
    user_oid: str,
    group_id: str,
    permission=Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    result = crud.delete_ownership(db, group_id, user_oid)
    if result is None:
        raise HTTPException(404, "グループまたはユーザーが見つかりません")
    return {"OK": True}


@app.post(
    "/groups",
    response_model=List[schemas.Group],
    summary="新規Groupの作成",
    tags=["groups"],
    description='### 必要な権限\nAdmin\n### ログインが必要か\nはい\n### 説明\n- オブジェクトではなく配列の形でjsonを渡してください\n- 複数のGroupの一括作成ができます\n- 各種URLを指定せずに作成する場合は、"twitter_url":""のように空文字ではなくパラメータ自体をjsonに記述せずNoneにしてください',
)
def create_group(
    groups: List[schemas.GroupCreate],
    permission: schemas.JWTUser = Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    result = []
    for group in groups:
        # idが命名規則に従っているかを確認する
        type: schemas.GroupType = group.type
        # 　クラス劇である時
        if type == schemas.GroupType.play:
            if not re.fullmatch(pattern=r"[1-3][1-8]r", string=group.id):
                raise HTTPException(
                    400,
                    "団体のタイプがplayである場合のidの命名規則に違反しています。命名規則:[1-3][1-8]r",
                )
        else:
            if re.fullmatch(pattern=r"[1-3][1-8]r", string=group.id):
                raise HTTPException(
                    400,
                    "団体のidがクラス劇のidと重複する可能性があります。クラス劇のidの命名規則から外れた値に変更してください。",
                )

        result.append(crud.create_group(db, group))
    return result


@app.get(
    "/groups",
    response_model=List[schemas.Group],
    summary="全Groupの情報を取得 [Redis TTL=" + str(REDIS_CACHE_EXPIRE) + "s]",
    tags=["groups"],
    description="Nuxt generate によってフロントエンドに全団体の情報は埋め込まれるため通常のユーザーがこのエンドポイントを操作することは無いが直接このエンドポイントにF5連打とかされてDB負荷増えたら嫌なので、Redis2分間キャッシュ \n ### 必要な権限\nなし\n### ログインが必要か\nいいえ",
)
def get_all_groups(db: Session = Depends(db.get_db)):
    cacheresult = redis_get_if_possible("groups")
    if cacheresult:
        return json.loads(cacheresult)
    groups = crud.get_all_groups_public(db)
    groups_serializable = []
    for g in groups:
        groups_serializable.append(schemas.Group.from_orm(g).dict())
    redis_set_if_possible(
        "groups", json.dumps(groups_serializable), ex=REDIS_CACHE_EXPIRE
    )
    return groups


@app.get(
    "/groups/{group_id}",
    response_model=schemas.Group,
    summary="指定されたGroupの情報を取得 [Redis TTL=" + str(REDIS_CACHE_EXPIRE) + "s]",
    tags=["groups"],
    description="### 必要な権限\nなし\n### ログインが必要か\nいいえ",
    responses={"404": {"description": "指定されたGroupが見つかりません"}},
)
def get_group(group_id: str, db: Session = Depends(db.get_db)):
    cacheresult = redis_get_if_possible("group:" + group_id)
    if cacheresult:
        return json.loads(cacheresult)
    group_result = crud.get_group_public(db, group_id)
    if not group_result:
        raise HTTPException(404, "指定されたGroupが見つかりません")
    redis_set_if_possible(
        "group:" + group_result.id,
        json.dumps(schemas.Group.from_orm(group_result).dict()),
        ex=REDIS_CACHE_EXPIRE,
    )
    return group_result


@app.put(
    "/groups/{group_id}",
    response_model=schemas.Group,
    summary="Groupを更新",
    tags=["groups"],
    description="### 必要な権限\nAdmin・当該グループのOwner・チーフ\n### ログインが必要か\nはい",
    responses={"404": {"description": "指定されたGroupまたはTagが見つかりません"}},
)
def update_group(
    group_id: str,
    updated_group: schemas.GroupUpdate,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    group = crud.get_group_public(db, group_id)
    if not (
        auth.check_admin(user)
        or auth.check_chief(user)
        or crud.check_owner_of(db, user, group.id)
    ):
        raise HTTPException(
            401, "Admin・当該GroupのOwner・チーフのいずれかの権限が必要です"
        )
    if (
        not updated_group.public_thumbnail_image_url
        and group.public_thumbnail_image_url
    ):  # サムネイル画像を削除する場合
        blob_storage.delete_image(group.public_thumbnail_image_url)
    u = crud.update_group(db, group, updated_group)
    return u


@app.put(
    "/groups/{group_id}/public_thumbnail_image",
    response_model=schemas.Group,
    summary="指定されたGroupのサムネイル画像をアップロード",
    tags=["groups"],
    description="### 必要な権限\nAdmin,当該GroupのOwner\n### ログインが必要か\nはい",
    responses={
        "404": {"description": "指定されたGroupが見つかりません"},
        "401": {"description": "Adminまたは当該GroupのOwnerの権限が必要です"},
    },
)
def upload_thumbnail_image(
    group_id: str,
    file: Union[bytes, None] = File(default=None),
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    group = crud.get_group_public(db, group_id)
    if not group:
        raise HTTPException(404, "指定されたGroupが見つかりません")
    if not (auth.check_admin(user) or crud.check_owner_of(db, user, group.id)):
        raise HTTPException(401, "Adminまたは当該GroupのOwnerの権限が必要です")
    if group.public_thumbnail_image_url:  # 既にサムネイル画像がある場合は削除
        blob_storage.delete_image(group.public_thumbnail_image_url)
    if file:
        image_url = blob_storage.upload_to_blob_public(file)
        return crud.change_public_thumbnail_image_url(db, group, image_url)
    else:
        return crud.change_public_thumbnail_image_url(db, group, None)


@app.put(
    "/groups/{group_id}/tags",
    summary="指定されたGroupにタグを紐づける",
    tags=["groups"],
    description="### 必要な権限\nAdminまたは当該グループのOwner\n### ログインが必要か\nはい",
    responses={"404": {"description": "指定されたGroupまたはTagが見つかりません"}},
)
def add_tag(
    group_id: str,
    tag_id: schemas.GroupTagCreate,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    group = crud.get_group_public(db, group_id)
    if not group:
        raise HTTPException(404, "指定されたGroupが見つかりません")
    if not (auth.check_admin(user) or crud.check_owner_of(db, user, group.id)):
        raise HTTPException(401, "Adminまたは当該GroupのOwnerの権限が必要です")
    grouptag = crud.add_tag(db, group_id, tag_id)
    if not grouptag:
        raise HTTPException(404, "Tagが見つかりません")
    tag = crud.get_tag(db, tag_id.tag_id)
    return "Add Tag Successfully"


@app.delete(
    "/groups/{group_id}/tags/{tag_id}",
    summary="指定されたGroupに紐づいている指定されたTagを削除",
    tags=["groups"],
    description="### 必要な権限\nAdminまたは当該グループのOwner\n### ログインが必要か\nはい\n",
    responses={
        "404": {
            "description": "- 指定されたGroupが見つかりません\n- 指定されたTagが見つかりません"
        }
    },
)
def delete_grouptag(
    group_id: str,
    tag_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    group = crud.get_group_public(db, group_id)
    if not group:
        raise HTTPException(404, "指定されたGroupが見つかりません")
    if not (auth.check_admin(user) or crud.check_owner_of(db, user, group.id)):
        raise HTTPException(401, "Adminまたは当該GroupのOwnerの権限が必要です")
    tag = crud.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(404, "指定されたTagが見つかりません")
    tag = crud.get_tag(db, tag_id)
    return crud.delete_grouptag(db, group, tag)


@app.delete(
    "/groups/{group_id}",
    summary="指定されたGroupを削除",
    tags=["groups"],
    description="### 必要な権限\nAdmin\n### ログインが必要か\nはい\n### 説明\n指定するGroupに紐づけられているEvent,Ticket,Tagをすべて削除しないと削除できません",
    responses={
        "404": {"description": "指定されたGroupが見つかりません"},
        "400": {
            "description": "指定されたGroupに紐づけられているEvent,Ticket,Tagをすべて削除しないと削除できません"
        },
    },
)
def delete_group(
    group_id: str,
    permission: schemas.JWTUser = Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    group = crud.get_group_public(db, group_id)
    if not group:
        raise HTTPException(404, "指定されたGroupが見つかりません")
    try:
        crud.delete_group(db, group)
        return {"OK": True}
    except:
        raise HTTPException(
            400,
            "指定されたGroupに紐づけられているEvent,Ticket,Tagをすべて削除しないと削除できません",
        )


@app.get(
    "/groups/{group_id}/links",
    summary="指定されたGroupのリンクを取得",
    response_model=List[schemas.GroupLink],
    tags=["groups"],
    description="### 必要な権限\nなし\n### ログインが必要か\nいいえ",
    responses={"404": {"description": "指定されたGroupが見つかりません"}},
)
def get_grouplinks(group_id: str, db: Session = Depends(db.get_db)):
    group = crud.get_group_public(db, group_id)
    if not group:
        raise HTTPException(404, "指定されたGroupが見つかりません")
    return crud.get_grouplinks_of_group(db, group)


@app.post(
    "/groups/{group_id}/links",
    summary="指定されたGroupにリンクを追加",
    tags=["groups"],
    description="### 必要な権限\nAdmin・当該グループのOwner・チーフ\n### ログインが必要か\nはい",
    responses={"404": {"detail": "指定されたGroupが見つかりません"}},
)
def add_grouplink(
    group_id: str,
    link: schemas.GroupLinkCreate,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    group = crud.get_group_public(db, group_id)
    if not group:
        raise HTTPException(404, "指定されたGroupが見つかりません")

    # check_chiefでadminも通しているのでcheck_adminは本当は必要ないがわかりやすいように残しておく
    if not (
        auth.check_admin(user)
        or auth.check_chief(user)
        or crud.check_owner_of(db, user, group.id)
    ):
        raise HTTPException(401, "Admin・当該GroupのOwner・チーフの権限が必要です")

    return crud.add_grouplink(db, group.id, link.linktext, link.name)


@app.delete(
    "/groups/{group_id}/links/{grouplink_id}",
    summary="指定されたGroupのリンクの削除",
    tags=["groups"],
    description="### 必要な権限\nAdmin・当該グループのOwner・チーフ\n### ログインが必要か\nはい",
    responses={"404": {"detail": "指定されたGroupが見つかりません"}},
)
def delete_grouplink(
    group_id: str,
    grouplink_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    gl: schemas.GroupLink = crud.get_grouplink(db, grouplink_id)
    if not gl:
        raise HTTPException(404, "指定されたGroupLinkが見つかりません")
    group = crud.get_group_public(db, gl.group_id)
    if not group:
        raise HTTPException(404, "指定されたGroupが見つかりません")

    # check_chiefでadminも通しているのでcheck_adminは本当は必要ないがわかりやすいように残しておく
    if not (
        auth.check_admin(user)
        or auth.check_chief(user)
        or crud.check_owner_of(db, user, group.id)
    ):
        raise HTTPException(401, "Admin・当該GroupのOwner・チーフの権限が必要です")
    return crud.delete_grouplink(db, grouplink_id)


### Event Crud
@app.post(
    "/groups/{group_id}/events",
    response_model=schemas.Event,
    summary="新規Eventを作成",
    tags=["events"],
    description="### 必要な権限\nadmin\n### ログインが必要か\nはい\n### 説明\n- 公演を作成します。",
    responses={
        "400": {"description": "パラメーターが不適切です"},
        "403": {"description": "Adminの権限が必要です"},
        "404": {"description": "指定されたGroupが見つかりません"},
    },
)
def create_event(
    group_id: str,
    event: schemas.EventCreate,
    user: schemas.JWTUser = Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    group = crud.get_group_public(db, group_id)
    if not group:
        raise HTTPException(404, "指定されたGroupが見つかりません")
    if event.starts_at > event.ends_at:
        raise HTTPException(400, "公演の開始時刻は終了時刻よりも前である必要があります")
    if event.sell_starts > event.sell_ends:
        raise HTTPException(
            400, "配布開始時刻は配布終了時刻よりも前である必要があります"
        )
    result = crud.create_event(db, group_id, event)
    if not result:
        raise HTTPException(400, "パラメーターが不適切です")
    return result


@app.get(
    "/groups/{group_id}/events",
    response_model=List[schemas.Event],
    summary="指定されたGroupの全Eventを取得 [Redis TTL="
    + str(REDIS_CACHE_EXPIRE)
    + "s]",
    tags=["events"],
    description="### 必要な権限\nなし\n### ログインが必要か\nいいえ\n",
)
def get_all_events(group_id: str, db: Session = Depends(db.get_db)):
    cacheresult = redis_get_if_possible("groupevents:" + group_id)
    if cacheresult:
        return json.loads(cacheresult)
    groupevents = crud.get_all_events(db, group_id)
    groupevents_serializable = []
    for e in groupevents:
        groupevents_serializable.append(
            schemas.EventDBOutput_fromEvent(schemas.Event.from_orm(e)).dict()
        )
    redis_set_if_possible(
        "groupevents:" + group_id,
        json.dumps(groupevents_serializable),
        ex=REDIS_CACHE_EXPIRE,
    )
    return groupevents


@app.get(
    "/groups/{group_id}/events/{event_id}",
    response_model=schemas.Event,
    summary="指定されたGroupの指定されたEevntを取得 [Redis TTL="
    + str(REDIS_CACHE_EXPIRE)
    + "s]",
    tags=["events"],
    description="### 必要な権限\nなし\n### ログインが必要か\nいいえ\n",
    responses={"404": {"description": "指定されたGroupまたはEventが見つかりません"}},
)
def get_event(group_id: str, event_id: str, db: Session = Depends(db.get_db)):
    cacheresult = redis_get_if_possible("group:" + group_id + "-event:" + event_id)
    if cacheresult:
        return json.loads(cacheresult)
    event = crud.get_event(db, event_id)
    if not event:
        raise HTTPException(404, "指定されたGroupまたはEventが見つかりません")
    redis_set_if_possible(
        "group:" + event.group_id + "-event:" + event.id,
        json.dumps(
            schemas.EventDBOutput_fromEvent(schemas.Event.from_orm(event)).dict()
        ),
        ex=REDIS_CACHE_EXPIRE,
    )
    return event


@app.delete(
    "/groups/{group_id}/events/{event_id}",
    summary="指定されたGroupの指定されたEventを削除",
    tags=["events"],
    description="### 必要な権限\nadmin\n### ログインが必要か\nはい\n### 説明\n指定するEventに紐づけられたTicketを全て削除しないと削除できません",
    responses={
        "404": {"description": "指定されたGroupまたはEventがありません"},
        "403": {"description": "Adminの権限が必要です"},
        "400": {"description": "既に整理券が取得されている公演は削除できません"},
    },
)
def delete_events(
    group_id: str,
    event_id: str,
    user: schemas.JWTUser = Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    event = crud.get_event(db, event_id)
    if not event:
        raise HTTPException(404, "指定されたGroupまたはEventがありません")
    group = crud.get_group_public(db, event.group_id)
    try:
        crud.delete_events(db, event)
        return {"OK": True}
    except:
        raise HTTPException(400, "既に整理券が取得されている公演は削除できません")


@app.get(
    "/groups/{group_id}/events/{event_id}/tickets/active",
    summary="指定されたイベントに対するすべてのアクティブ状態の整理券IDを返す",
    tags=["events"],
    description="### 必要な権限\nstudents\n### ログインが必要か\nはい\n### 説明\n指定された公演に対するすべてのアクティブ状態の整理券のIDを返します",
)
def get_all_active_tickets_of_event(
    group_id: str,
    event_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    if not auth.check_students(user):
        raise HTTPException(403, "生徒である必要があります。")
    return crud.get_all_active_tickets_of_event(db, event_id)


### Ticket CRUD
@app.post(
    "/spectest/groups/{group_id}/events/{event_id}/tickets",
    response_model=schemas.Ticket,
    description="ツールを用いた負荷テスト用のエンドポイントです。同じ時間帯の公演を取っているか、同じ公演を取っているかの確認をしないので、一つのアカウントで複数のチケットを取ることができます。大量のチケットを実際に作成するので削除しやすいgroupとeventを指定することを推奨します。",
    summary="整理券取得の負荷テスト",
)
def spectest_ticket(
    group_id: str,
    event_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    event = crud.get_event(db, event_id)
    if not event:
        raise HTTPException(404, "指定されたGroupまたはEventが見つかりません")
    if not auth.check_school(user):
        raise HTTPException(HTTP_403_FORBIDDEN)

    if crud.count_tickets_for_event(db, event) + 1 <= event.ticket_stock:
        res = crud.spectest_ticket(group_id, event_id, db, user)
    else:
        raise HTTPException(404, "already max")

    return res


@app.post(
    "/groups/{group_id}/events/{event_id}/tickets",
    response_model=schemas.Ticket,
    summary="整理券取得",
    tags=["tickets"],
    description="### 必要な権限\nアクティブ(校内に来場済み)なユーザーであること\n### ログインが必要か\nはい\n### 説明\n整理券取得できる条件\n- ユーザーが校内に来場ずみ\n- 現在時刻が取りたい整理券の配布時間内\n- 当該公演の整理券在庫が余っている\n- ユーザーは既にこの整理券を取得していない\n- ユーザーは既に当該公演と同じ時間帯の公演の整理券を取得していない\n- 同時入場人数は3名まで(***Azure ADのアカウントは1人という制約は無くしました***)",
    responses={
        "404": {
            "description": "- 指定されたGroupまたはEventが見つかりません\n- 既にこの公演・この公演と同じ時間帯の公演の整理券を取得している場合、新たに取得はできません\n- この公演の整理券は売り切れています\n- 現在整理券の配布時間外です"
        },
        "400": {
            "description": "- 同時入場人数は3人まで(***Azure ADのアカウントは1人という制約は無くしました***)です\n- 校内への来場処理をしたユーザーのみが整理券を取得できます"
        },
    },
)
def create_ticket(
    group_id: str,
    event_id: str,
    person: int,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    event = crud.get_event(db, event_id)
    if not event:
        raise HTTPException(404, "指定されたGroupまたはEventが見つかりません")
    if not auth.check_role(event.target, user):
        raise HTTPException(
            HTTP_403_FORBIDDEN, "この公演は整理券を取得できる人が制限されています。"
        )

    if (
        event.sell_starts < datetime.now(timezone(timedelta(hours=+9)))
        and datetime.now(timezone(timedelta(hours=+9))) < event.sell_ends
    ):
        qualified: bool = crud.check_qualified_for_ticket(db, event, user)
        if (
            crud.count_tickets_for_event(db, event) + person <= event.ticket_stock
            and qualified
        ):  ##まだチケットが余っていて、同時間帯の公演の整理券取得ではない
            if 0 < person < 4:  # 1アカウントにつき3人まで入れる
                return crud.create_ticket(db, event, user, person)
            else:
                raise HTTPException(400, "同時入場人数は3人までです")
        elif not qualified:
            raise HTTPException(
                404,
                "既にこの公演・この公演と重複する時間帯の公演の整理券を取得している場合、新たに取得はできません。または取得できる整理券の枚数の上限を超えています",
            )
        else:
            raise HTTPException(404, "この公演の整理券は売り切れています")
    else:
        raise HTTPException(404, "現在整理券の配布時間外です")


@app.post(
    "/groups/{group_id}/events/{event_id}/tickets/admin",
    response_model=schemas.Ticket,
    summary="条件を無視して余っていたら整理券を取得",
    tags=["tickets", "admin"],
    description="### 必要な権限\nAdmin\n### ログインが必要か\nはい\n### 説明\n整理券が余っているのなら時間・時間の重なりを無視して強制的に整理券を取得",
)
def create_ticket_admin(
    group_id: str,
    event_id: str,
    person: int,
    user: schemas.JWTUser = Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    event = crud.get_event(db, event_id)
    if not event:
        raise HTTPException(404, "指定されたGroupまたはEventが見つかりません")
    if not auth.check_role(event.target, user):
        raise HTTPException(
            HTTP_403_FORBIDDEN, "この公演は整理券を取得できる人が制限されています。"
        )

    if (
        crud.count_tickets_for_event(db, event) + person <= event.ticket_stock
    ):  ##まだチケットが余っていて、同時間帯の公演の整理券取得ではない
        if 0 < person < 4:  # 1アカウントにつき3人まで入れる
            return crud.create_ticket(db, event, user, person)
        else:
            raise HTTPException(400, "同時入場人数は3人までです")
    else:
        raise HTTPException(404, "この公演の整理券は売り切れています")


@app.post(
    "/groups/{group_id}/events/{event_id}/tickets/family",
    response_model=schemas.Ticket,
    summary="家族優先券整理券取得",
    tags=["tickets"],
    description="### 必要な権限\n生徒の保護者である\n### ログインが必要か\nはい\n### 説明\n整理券取得できる条件\n- 現在時刻が取りたい整理券の優先券配布時間内\n- 当該公演の整理券在庫が余っている\n- ユーザーは既にこの整理券を取得していない\n- ユーザーは既に当該公演と同じ時間帯の公演の整理券を取得していない\n- 同時入場人数は1名まで(***Azure ADのアカウントは1人という制約は無くしました***)\n- 保護者がそのクラスの保護者として登録されている",
    responses={
        "404": {
            "description": "- 指定されたGroupまたはEventが見つかりません\n- 既にこの公演・この公演と同じ時間帯の公演の整理券を取得している場合、新たに取得はできません\n- この公演の整理券は売り切れています\n- 現在整理券の配布時間外です"
        },
        "400": {
            "description": "- 同時入場人数は3人まで(***Azure ADのアカウントは1人という制約は無くしました***)です\n- 校内への来場処理をしたユーザーのみが整理券を取得できます"
        },
    },
)
def create_family_ticket(
    group_id: str,
    event_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    event = crud.get_event(db, event_id)

    # チェック
    if not crud.is_parent_belong_to(group_id=group_id, user=user):
        raise HTTPException(
            403, "アカウントが指定された団体に保護者として登録されていません。"
        )
    if not event:
        raise HTTPException(404, "指定されたGroupまたはEventが見つかりません")
    if not auth.check_role(event.target, user):
        raise HTTPException(
            HTTP_403_FORBIDDEN, "この公演は整理券を取得できる人が制限されています。"
        )

    # 優先券配布開始時間よりも現在時刻が後
    if datetime.fromisoformat(settings.family_ticket_sell_starts) < datetime.now(
        timezone(timedelta(hours=+9))
    ):
        # チケットがまだ余っている
        if crud.count_tickets_for_event(db, event) + 1 <= event.ticket_stock:
            if crud.count_taken_family_ticket(db, user) < 2:
                return crud.create_ticket(db, event, user, 1, True)
            else:
                raise HTTPException(404, "既に保護者用優先券を2枚以上取得しています。")
        else:
            raise HTTPException(404, "この公演の整理券は売り切れています")
    else:
        raise HTTPException(404, "現在優先券の配布時間外です")


@app.get(
    "/groups/{group_id}/events/{event_id}/tickets",
    response_model=schemas.TicketsNumberData,
    summary="指定された公演の整理券の枚数情報を取得 [Redis TTL=15s]",
    tags=["tickets"],
    description='結果はRedisに "tickets-numberdata-<Event.id>" というキーでキャッシュされます(TTL=15) \n ### 必要な権限\nなし\n### ログインが必要か\nいいえ\n',
    responses={
        "404": {
            "description": "- 指定されたGroupが見つかりません\n- 指定されたEventが見つかりません"
        }
    },
)
def count_tickets(group_id: str, event_id: str, db: Session = Depends(db.get_db)):
    cacheresult = redis_get_if_possible("tickets-numberdata-" + event_id)
    if cacheresult:
        return json.loads(cacheresult)
    event = crud.get_event(db, event_id)
    if not event:
        raise HTTPException(404, "指定されたEventが見つかりません")
    taken_tickets: int = crud.count_tickets_for_event(db, event)
    stock: int = event.ticket_stock
    left_tickets: int = stock - taken_tickets
    tnd = schemas.TicketsNumberData(
        taken_tickets=taken_tickets, left_tickets=left_tickets, stock=stock
    )
    redis_set_if_possible("tickets-numberdata-" + event.id, tnd.json(), ex=15)
    return tnd


@app.delete(
    "/groups/{group_id}/events/{event_id}/tickets/{ticket_id}",
    summary="指定された整理券をキャンセル(削除)",
    tags=["tickets"],
    description="### 必要な権限\n指定された整理券のオーナー\n### ログインが必要か\nはい\n",
    responses={"403": {"description": "指定された整理券の所有者である必要があります"}},
)
def delete_ticket(
    group_id: str,
    event_id: str,
    ticket_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket.owner_id == auth.user_object_id(user):
        raise HTTPException(403, "指定された整理券の所有者である必要があります")
    try:
        crud.delete_ticket(db, ticket)
        return {"OK": True}
    except:
        raise HTTPException(500)


@app.get(
    "/tickets/{ticket_id}",
    response_model=schemas.Ticket,
    summary="指定された整理券の情報を取得",
    tags=["tickets"],
    description="### 必要な権限\nschool(暫定)\n### ログインが必要か\nはい\n### 説明\n総当たり攻撃を防ぐため、指定された整理券は存在するが権限が無い場合も404を返す",
    responses={"404": {"description": "- 指定された整理券が見つかりません"}},
)
def get_ticket(
    ticket_id: str,
    user: schemas.JWTUser = Depends(auth.school),
    db: Session = Depends(db.get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(404, "指定された整理券が見つかりません")
    return ticket


@app.put(
    "/tickets/{ticket_id}",
    response_model=schemas.Ticket,
    summary="指定された整理券をもぎる",
    tags=["tickets"],
    description="### 必要な権限\nschool\n### ログインが必要か\nはい\n### 説明\n総当たり攻撃を防ぐため、指定された整理券は存在するが権限が無い場合も404を返す",
)
def use_ticket(
    ticket_id: str,
    permission: schemas.JWTUser = Depends(auth.school),
    db: Session = Depends(db.get_db),
):
    if crud.check_ticket_available(db, ticket_id):
        result = crud.use_ticket(db, ticket_id)
        return result
    raise HTTPException(404, "整理券は使用済み、または存在しません。")


@app.post(
    "/chief/groups/{group_id}/events/{event_id}/tickets",
    response_model=schemas.Ticket,
    tags=["chief"],
    description="### 必要な権限\nchief\n### ログインが必要か\nはい\n ### 説明\n チーフ会が紙整理券を1枚とるエンドポイント",
)
def chief_create_ticket(
    group_id: str,
    event_id: str,
    user: schemas.JWTUser = Depends(auth.chief),
    db: Session = Depends(db.get_db),
):
    event = crud.get_event(db, event_id)
    if not event:
        raise HTTPException(404, "指定されたGroupまたはEventが見つかりません")
    if event.target != schemas.UserRole.paper:
        raise HTTPException(400, "これは紙整理券の公演ではありません")
    if crud.count_tickets_for_event(db, event) >= event.ticket_stock:
        raise HTTPException(404, "売り切れました")
    result = crud.chief_create_ticket(db, event, user, 1)
    return result


@app.delete(
    "/chief/groups/{group_id}/events/{event_id}/tickets",
    tags=["chief"],
    description="### 必要な権限\nchief\n### ログインが必要か\nはい\n ### 説明\n チーフ会が紙整理券を1枚減らすエンドポイント",
)
def chief_delete_ticket(
    group_id: str,
    event_id: str,
    permission: schemas.JWTUser = Depends(auth.chief),
    db: Session = Depends(db.get_db),
):
    event = crud.get_event(db, event_id)
    if not event:
        raise HTTPException(404, "指定されたGroupまたはEventが見つかりません")
    if event.target != schemas.UserRole.paper:
        raise HTTPException(400, "これは紙整理券の公演ではありません")
    # if crud.count_tickets_for_event(db,event)>=event.ticket_stock:
    #    raise HTTPException(400,"取得されている整理券が0枚です")
    crud.chief_delete_ticket(db, event)
    return {"OK": True}


@app.get(
    "/tickets/{ticket_id}/available",
    response_model=bool,
    summary="整理券が有効なものかを判定",
    tags=["tickets"],
    description="### 必要な権限\nなし\n### ログインが必要か\nはい\n選択された整理券がactiveな状態であるときTrueを返す",
)
def check_ticket_available(
    ticket_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    return crud.check_ticket_available(db, ticket_id)


### Vote Crud
@app.post(
    "/votes",
    response_model=schemas.Vote,
    summary="投票",
    tags=["votes"],
    description="### 必要な権限\nparents, guest\n### ログインが必要か\nはい\n### 説明\n- 投票できるのはguestとparentsのみです。一アカウントにつき一回限りです",
)
def create_vote(
    group_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    if not (auth.check_parents(user) or auth.check_guest(user)):
        raise HTTPException(400, "ゲストまたは保護者である必要があります")

    # Groupが存在するかの判定も下で兼ねられる
    isVoted = True if crud.get_user_vote_count(db, user) >= 2 else False

    if isVoted:
        raise HTTPException(400, "投票は1人2回までです")

    if not crud.get_user_votable(db, user, group_id):
        raise HTTPException(
            400, "すでにその団体に対して投票済みまたは有効な整理券がありません。"
        )

    return crud.create_vote(db, group_id, user)


@app.get(
    "/votes/{group_id}",
    response_model=schemas.GroupVotesResponse,
    summary="Groupへの投票数を確認",
    tags=["votes"],
    description="### 必要な権限\nAdminまたは当該グループのOwner \n### ログインが必要か\nはい\n",
    responses={
        "404": {"detail": "指定された団体が見つかりません"},
        "401": {"detail": "Adminまたはchiefである必要があります"},
    },
)
def get_group_votes(
    group_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    # auth.check_chiefでadminも通るのでadminかの判定はいらないがわかりやすいようにauth.check_adminも書いておく
    if not (auth.check_admin(user) or auth.check_chief(user)):
        raise HTTPException(401, "Adminまたはchiefである必要があります")
    g = crud.get_group_public(db, group_id)
    if g is None:
        raise HTTPException(404, "指定された団体が見つかりません")
    return schemas.GroupVotesResponse(
        group_id=g.id, votes_num=crud.get_group_votes(db, g)
    )


@app.get(
    "/users/me/votable",
    response_model=bool,
    summary="userが投票可能かを確認",
    tags=["votes"],
    description="### 必要な権限\nなし\n### ログインが必要か\nはい",
)
def get_user_votable(
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    if crud.get_user_vote_count(db, user) < 2:
        return True
    return False


@app.get(
    "/users/me/votes/{group_id}",
    response_model=bool,
    summary="指定された団体に投票可能かを判定",
    tags=["votes"],
    description="指定された団体に対して投票可能かを返す\n### 判定項目\n- 整理券の有効性\n- 団体に対して投票済みか\n- 既に投票している回数（2回以上投票している場合投票不可）",
)
def get_user_votable_group(
    group_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    if crud.get_user_vote_count(db, user) >= 2:
        return False

    return crud.get_user_votable(db, user, group_id)


# urlを/users/me/votes/countにすると/users/me/votes/{group_id}と認識されて間違った関数が実行される
@app.get(
    "/users/me/count/votes",
    response_model=int,
    summary="ユーザーが投票した数を返します",
    tags=["votes"],
    description="ユーザーが投票した数を返します",
)
def get_user_vote_count(
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    return crud.get_user_vote_count(db, user)


@app.get(
    "/users/me/votes",
    response_model=List[schemas.Vote],
    summary="userの投票を返す",
    description="userが投票した投票情報を返す",
    tags=["votes"],
)
def get_user_votes(
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    return crud.get_user_votes(db, user)


# Tag
@app.post(
    "/tags",
    response_model=List[schemas.Tag],
    summary="新規Tagの作成",
    tags=["tags"],
    description="### 必要な権限\nAdmin\n### ログインが必要か\nはい\n",
)
def create_tag(
    tags: List[schemas.TagCreate],
    permission: schemas.JWTUser = Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    result = []
    for tag in tags:
        result.append(crud.create_tag(db, tag))
    return result


@app.get(
    "/tags",
    response_model=List[schemas.Tag],
    summary="全Tagを取得",
    tags=["tags"],
    description="### 必要な権限\nなし\n### ログインが必要か\nいいえ",
)
def get_all_tags(db: Session = Depends(db.get_db)):
    return crud.get_all_tags(db)


@app.get(
    "/tags/{tag_id}",
    response_model=schemas.Tag,
    summary="指定されたTagを取得",
    tags=["tags"],
    description="### 必要な権限\nなし\n### ログインが必要か\nいいえ\n",
    responses={"404": {"description": "指定されたTagが見つかりません"}},
)
def get_tag(tag_id: str, db: Session = Depends(db.get_db)):
    tag_result = crud.get_tag(db, tag_id)
    if not tag_result:
        raise HTTPException(404, "指定されたTagが見つかりません")
    return tag_result


@app.put(
    "/tags/{tag_id}",
    response_model=schemas.Tag,
    summary="Tagの名前を変更",
    tags=["tags"],
    description="### 必要な権限\nAdmin\n### ログインが必要か\nはい",
    responses={"404": {"description": "指定されたTagが見つかりません"}},
)
def change_tag_name(
    tag_id: str,
    tag: schemas.TagCreate,
    permission: schemas.JWTUser = Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    tag_result = crud.put_tag(db, tag_id, tag)
    if not tag_result:
        raise HTTPException(404, "指定されたTagが見つかりません")
    return tag_result


@app.delete(
    "/tags/{tag_id}",
    summary="指定されたTagの削除",
    tags=["tags"],
    description="### 必要な権限\nAdmin\n### ログインが必要か\nはい\n",
    responses={"404": {"description": "指定されたTagが見つかりません"}},
)
def delete_tag(
    tag_id: str,
    permission: schemas.JWTUser = Depends(auth.admin),
    db: Session = Depends(db.get_db),
):
    result = crud.delete_tag(db, tag_id)
    if result == None:
        raise HTTPException(404, "指定されたTagが見つかりません")
    return "Successfully Deleted"


@app.get(
    "/ga/screenpageview",
    response_model=schemas.GAScreenPageViewResponse,
    summary="Google Analyticsのビュー数を取得 [Redis TTL=60s]",
    tags=["ga"],
    description="### 必要な権限\nなし\n### ログインが必要か\nいいえ\n### 説明\nGoogle Analyticsのビュー数を取得します \n start_dateとend_dateの形式：YYYY-MM-DD, NdaysAgo, yesterday, or today \n page_path は/から始まる相対パス(/はurlで送れないのでURL Encodeする) \n Redisで1分毎にキャッシュしています",
)
def get_ga_screenpageview(start_date: str, end_date: str, page_path: str):
    return {
        "start_date": start_date,
        "end_date": end_date,
        "page_path": page_path,
        "view": ga_screenpageview(start_date, page_path, end_date),
    }


# @app.put("/admin/user")


@app.post(
    "/admin/update_frontend",
    summary="フロントエンドの更新",
    tags=["admin"],
    description="### 必要な権限\nAdmin\n### ログインが必要か\nはい\n quaint-appのmainブランチの内容をもとにビルドしてCloudflareにデプロイ",
)
def update_frontend(permission: schemas.JWTUser = Depends(auth.admin)):
    res = requests.post(settings.cloudflare_deploy_hook_url)
    if res.status_code == 200:
        return "OK"
    else:
        HTTPException(res.status_code, "Cloudflareへのデプロイに失敗しました")


@app.post(
    "/support/events",
    summary="公演の一括追加",
    tags=["admin"],
    description="csvファイルを元に公演を一斉に追加します。csvファイルについてはサンプルのエクセルと同じ書式で書いたものにしてください。正しく処理されません。",
)
async def create_all_events_from_csv(
    file: UploadFile = File(...),
    permission: schemas.JWTUser = Depends(auth.chief),
    db: Session = Depends(db.get_db),
):
    # pandasのDataFrameに読み込んだファイルを変換
    content = file.file.read()
    string_data = str(content, "utf-8")
    data = StringIO(string_data)
    df = pd.read_csv(data)
    data.close()
    file.file.close()

    converted_df = crud.convert_df(df)
    crud.check_df(db, converted_df)
    crud.create_events_from_df(db, converted_df)

    return {
        "message": [converted_df.iloc[i, :].to_json() for i in range(len(converted_df))]
    }


@app.get(
    "/hebe/nowplaying",
    response_model=schemas.HebeResponse,
    summary="今やっているHebeの団体IDを取得",
    tags=["chief"],
)
def get_hebe_nowplaying(db: Session = Depends(db.get_db)):
    h = crud.get_hebe_nowplaying(db)
    if h is not None:
        return h
    hh = schemas.HebeResponse(group_id="")
    return hh


@app.get(
    "/hebe/upnext",
    response_model=schemas.HebeResponse,
    summary="次のHebeの団体IDを取得",
    tags=["chief"],
)
def get_hebe_upnext(db: Session = Depends(db.get_db)):
    h = crud.get_hebe_upnext(db)
    if h is not None:
        return h
    hh = schemas.HebeResponse(group_id="")
    return hh


@app.post(
    "/hebe/nowplaying",
    response_model=schemas.HebeResponse,
    summary="今やっているHebeの団体IDを設定",
    tags=["chief"],
    description="チーフのみ",
)
def set_hebe_nowplaying(
    hebe: schemas.HebeResponse,
    permission: schemas.JWTUser = Depends(auth.chief),
    db: Session = Depends(db.get_db),
):
    return crud.set_hebe_nowplaying(db, hebe)


@app.post(
    "/hebe/upnext",
    response_model=schemas.HebeResponse,
    summary="次のHebeの団体IDを設定",
    tags=["chief"],
    description="チーフのみ",
)
def set_hebe_upnext(
    hebe: schemas.HebeResponse,
    permission: schemas.JWTUser = Depends(auth.chief),
    db: Session = Depends(db.get_db),
):
    return crud.set_hebe_upnext(db, hebe)


@app.get(
    "/news",
    response_model=List[schemas.NewsBase],
    summary="全てのお知らせ情報を取得する",
    tags=["news"],
)
def get_all_news(db: Session = Depends(db.get_db)):
    return crud.get_all_news(db)


@app.get(
    "/news/{news_id}",
    summary="指定されたidのnewsを取得",
    response_model=schemas.NewsBase,
    tags=["news"],
)
def get_news(news_id: str, db: Session = Depends(db.get_db)):
    return crud.get_news(db, news_id)


@app.post(
    "/news/create",
    response_model=schemas.NewsUpdate,
    summary="お知らせ情報の作成",
    tags=["news", "chief", "admin"],
)
def create_news(
    news: schemas.NewsUpdate,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    if not (auth.check_admin(user) or auth.check_chief(user)):
        raise HTTPException(HTTP_403_FORBIDDEN, "Adminまたはチーフ会の権限が必要です")

    return crud.create_news(db, news)


@app.delete(
    "/news/{news_id}",
    response_model=schemas.NewsBase,
    summary="お知らせ情報の削除",
    tags=["news", "chief", "admin"],
)
def delete_news(
    news_id: str,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    if not (auth.check_admin(user) or auth.check_chief(user)):
        raise HTTPException(HTTP_403_FORBIDDEN, "Adminまたはチーフ会の権限が必要です")

    return crud.delete_news(db, news_id)


@app.put(
    "/news/{news_id}",
    summary="お知らせ情報の更新",
    response_model=schemas.NewsUpdate,
    description="タイムスタンプとIDは変更されません。注意してください。",
    tags=["news", "chief", "admin"],
)
def change_news(
    news_id: str,
    news: schemas.NewsUpdate,
    user: schemas.JWTUser = Depends(auth.get_current_user),
    db: Session = Depends(db.get_db),
):
    if not (auth.check_admin(user) or auth.check_chief(user)):
        raise HTTPException(HTTP_403_FORBIDDEN, "Adminまたはチーフ会の権限が必要です")

    return crud.update_news(db, news_id, news)
