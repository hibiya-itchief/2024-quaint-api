from datetime import datetime, timedelta, timezone
import json
from urllib import response
import ulid

from app import crud, schemas, models
from app.config import settings
from app.main import app
from app.test import factories

from fastapi import Depends
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from requests import Session
from typing_extensions import assert_type

client = TestClient(app)

def test_read_root_success():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "title": "QUAINT-API",
        "description":"日比谷高校オンライン整理券システム「QUAINT」のAPI"
    }

# users test
def test_users_me_ticket(db):
    # create group
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # create event
    event = crud.create_event(db, group1.id, factories.group1_event)

    # create ticket
    db_ticket = models.Ticket(id=ulid.new().str, group_id=group1.id, event_id=event.id, owner_id=factories.valid_student_user['oid'], person=1,status="active",created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)

    response = client.get("/users/me/tickets", headers=factories.authheader(factories.valid_student_user))

    assert response.status_code == 200

# もっと詳しくやる必要あり
def test_user_me_owner_of():
    response = client.get("/users/me/owner_of", headers=factories.authheader(factories.valid_admin_user))

    assert response.status_code == 200

def test_users_owner_of():
    response = client.get("/users/owner_of", headers=factories.authheader(factories.valid_admin_user))
    assert response.status_code == 200

# groups test
def test_get_all_groups(db):
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())
    db.add_all([group1,group2])
    db.flush()
    db.commit()
    response = client.get("/groups")

    assert response.status_code == 200

def test_create_single_group():
    response = client.post("/groups" ,json=factories.valid_single_group, headers=factories.authheader(factories.valid_admin_user))
    assert response.status_code == 200

def test_create_multiple_group_success():
    response = client.post(url="/groups",json=factories.valid_multiple_groups,headers=factories.authheader(factories.valid_admin_user))
    assert response.status_code==200
    
def test_get_group_information(db):
    crud.create_group(db,factories.group1)
    response = client.get(f"/groups/{factories.group1.id}")
    assert response.status_code == 200

def test_delete_group(db):
    crud.create_group(db, factories.group1)
    response = client.delete(f"/groups/{factories.group1.id}", headers=factories.authheader(factories.valid_admin_user))
    assert response.status_code == 200

def test_create_group_tag(db):
    crud.create_group(db, factories.group1)

    # create tag
    db_tag = models.Tag(id="test_tag_id", tagname="test")

    response_404 = client.put(f"/groups/{factories.group1.id}/tags", json={"tag_id":db_tag.id}, headers=factories.authheader(factories.valid_admin_user))
    assert response_404.status_code == 404

    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    response_200 = client.put(f"/groups/{factories.group1.id}/tags", json={"tag_id":db_tag.id}, headers=factories.authheader(factories.valid_admin_user))
    assert response_200.status_code == 200

def test_delete_group_tag(db):
    crud.create_group(db, factories.group1)
    db_tag = models.Tag(id="test", tagname="test_tag")
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    crud.add_tag(db, factories.group1.id, factories.group_tag_create1)

    response = client.delete(f"/groups/{factories.group1.id}/tags/{factories.group_tag_create1.tag_id}", headers=factories.authheader(factories.valid_admin_user))
    assert response.status_code == 200

# events

# tickets
# 優先券取得テスト
# 時間は正しい場合
def test_create_family_ticket(db):
    # 環境変数書き換え
    # テスト実行後に変数は元の値に戻してくれるみたい
    settings.family_ticket_sell_starts = (datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=-1)).isoformat()

    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())
    group3 = models.Group(**factories.group4.dict()) # factories.group3はtypeがtestなのでgroup4

    db.add_all([group1,group2, group3])
    db.flush()
    db.commit()

    events = []

    # 公演作成
    for i, group in enumerate([group1, group2, group3]):
        event_create = schemas.EventCreate(
                eventname='テスト公演',
                target='everyone',
                ticket_stock=20,
                starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=2 + i), # 優先券以外では取得不可の時間設定
                ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3 + i),
                sell_starts=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1, hours=+0),
                sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1, hours=+1)
            )
        event = crud.create_event(db, group.id, event_create)
        events.append(event)

    response_1 = client.post(f"/groups/{group1.id}/events/{events[0].id}/tickets/family", headers=factories.authheader(factories.valid_parent_user))
    assert response_1.status_code == 200
    response_2 = client.post(f"/groups/{group1.id}/events/{events[1].id}/tickets/family", headers=factories.authheader(factories.valid_parent_user))
    assert response_2.status_code == 200
    response_3 = client.post(f"/groups/{group1.id}/events/{events[2].id}/tickets/family", headers=factories.authheader(factories.valid_parent_user))
    assert response_3.status_code == 404

def test_create_family_ticket_wrong_time(db):
    # 環境変数書き換え
    # テスト実行後に変数は元の値に戻してくれるみたい
    settings.family_ticket_sell_starts = (datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1)).isoformat()

    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
                eventname='テスト公演',
                target='everyone',
                ticket_stock=20,
                starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=2), # 優先券以外では取得不可の時間設定
                ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
                sell_starts=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1, hours=+0),
                sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1, hours=+1)
            )
    event = crud.create_event(db, group1.id, event_create)

    response = client.post(f"/groups/{group1.id}/events/{event.id}/tickets/family", headers=factories.authheader(factories.valid_parent_user))
    assert response.status_code == 404

def test_create_family_ticket_invalid_user(db):
    # 環境変数書き換え
    # テスト実行後に変数は元の値に戻してくれるみたい
    settings.family_ticket_sell_starts = (datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1)).isoformat()

    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
                eventname='テスト公演',
                target='everyone',
                ticket_stock=20,
                starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=2), # 優先券以外では取得不可の時間設定
                ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
                sell_starts=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1, hours=+0),
                sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1, hours=+1)
            )
    event = crud.create_event(db, group1.id, event_create)

    response = client.post(f"/groups/{group1.id}/events/{event.id}/tickets/family", headers=factories.authheader(factories.valid_student_user))
    assert response.status_code == 403

# vote
# voteの作成・カウント
def test_vote(db):
    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())
    group3 = models.Group(**factories.group5.dict())

    db.add_all([group1,group2,group3])
    db.flush()
    db.commit()

    events = []

    # 公演作成
    for i, group in enumerate([group1, group2, group3]):
        event_create = schemas.EventCreate(
                eventname='テスト公演',
                target='everyone',
                ticket_stock=20,
                starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=1 + i),
                ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=2 + i),
                sell_starts=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=-1),
                sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=1)
            )
        event = crud.create_event(db, group.id, event_create)
        events.append(event)

    # チケット取得
    db_ticket_1 = models.Ticket(id=ulid.new().str,group_id=group1.id,event_id=events[0].id, owner_id=factories.valid_guest_user['oid'], person=1, status="active",created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat())
    db.add(db_ticket_1)
    db.commit()
    db.refresh(db_ticket_1)
    db_ticket_2 = models.Ticket(id=ulid.new().str,group_id=group2.id,event_id=events[1].id, owner_id=factories.valid_guest_user['oid'], person=1, status="active",created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat())
    db.add(db_ticket_2)
    db.commit()
    db.refresh(db_ticket_2)
    db_ticket_3 = models.Ticket(id=ulid.new().str, group_id=group3.id, event_id=events[2].id, owner_id=factories.valid_guest_user['oid'], person=1, status="active",created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat())
    db.add(db_ticket_3)
    db.commit()
    db.refresh(db_ticket_3)

    parent_db_ticket_1 = models.Ticket(id=ulid.new().str,group_id=group1.id,event_id=events[0].id, owner_id=factories.valid_parent_user['oid'], person=1, status="active",created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat())
    db.add(parent_db_ticket_1)
    db.commit()
    db.refresh(parent_db_ticket_1)

    student_db_ticket_1 = models.Ticket(id=ulid.new().str,group_id=group1.id,event_id=events[0].id, owner_id=factories.valid_student_user['oid'], person=1, status="active",created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat())
    db.add(student_db_ticket_1)
    db.commit()
    db.refresh(student_db_ticket_1)

    # 投票
    response_1 = client.post(url="/votes", params={"group_id":group1.id}, headers=factories.authheader(factories.valid_guest_user))
    assert response_1.status_code == 200

    response_2 = client.post(url="/votes", json=[group1.id, group2.id], headers=factories.authheader(factories.valid_guest_user))
    assert response_2.status_code == 422

    response_3 = client.get(url=f"/votes/{group1.id}", headers=factories.authheader(factories.valid_admin_user))
    assert response_3.status_code == 200
    assert response_3.json() == {"group_id": group1.id, "votes_num": 1}

    response_4 = client.post(url="/votes", params={"group_id":group2.id}, headers=factories.authheader(factories.valid_guest_user))
    assert response_4.status_code == 200

    response_5 = client.post(url="/votes", params={"group_id":group3.id}, headers=factories.authheader(factories.valid_guest_user))
    assert response_5.json() == {"detail":"投票は1人2回までです"}

    response_6 = client.post(url="/votes", params={"group_id":group1.id}, headers=factories.authheader(factories.valid_parent_user))
    assert response_6.status_code == 200

    response_7 = client.get(url=f"/votes/{group1.id}", headers=factories.authheader(factories.valid_admin_user))
    assert response_7.status_code == 200
    assert response_7.json() == {"group_id": group1.id, "votes_num": 2}

    response_8 = client.post(url="/votes", params={"group_id":group1.id}, headers=factories.authheader(factories.valid_student_user))
    assert response_8.json() == {"detail":"ゲストまたは保護者である必要があります"}

    response_9 = client.get(url=f"/users/me/votes/{group1.id}", headers=factories.authheader(factories.valid_guest_user))
    assert response_9.json() == True

    response_10 = client.get(url=f"/users/me/votes/{group2.id}", headers=factories.authheader(factories.valid_guest_user))
    assert response_10.json() == True

# userが投票可能か
def test_get_user_votable(db):
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())

    db.add_all([group1,group2])
    db.flush()
    db.commit()

    vote_1 = models.Vote(id=ulid.new().str, group_id=group1.id, user_id=factories.valid_guest_user['oid'])
    db.add(vote_1)
    db.commit()
    db.refresh(vote_1)

    response_1 =  client.get(url="/users/me/votable", headers=factories.authheader(factories.valid_guest_user))
    assert response_1.json() == True

    vote_2 = models.Vote(id=ulid.new().str, group_id=group2.id, user_id=factories.valid_guest_user['oid'])
    db.add(vote_2)
    db.commit()
    db.refresh(vote_2)

    response_2 =  client.get(url="/users/me/votable", headers=factories.authheader(factories.valid_guest_user))
    assert response_2.json() == False

# userの投票情報を取得
def test_get_user_votes(db):
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())

    db.add_all([group1,group2])
    db.flush()
    db.commit()

    vote_1 = models.Vote(id=ulid.new().str, group_id=group1.id, user_id=factories.valid_guest_user['oid'])
    db.add(vote_1)
    db.commit()
    db.refresh(vote_1)

    vote_2 = models.Vote(id=ulid.new().str, group_id=group2.id, user_id=factories.valid_guest_user['oid'])
    db.add(vote_2)
    db.commit()
    db.refresh(vote_2)

    response = client.get(url="/users/me/votes", headers=factories.authheader(factories.valid_guest_user))
    assert response.status_code == 200


#もっと細かく書けるかも(https://nmomos.com/tips/2021/03/07/fastapi-docker-8/#toc_id_2)
