import datetime
import json
import ulid
from urllib import response

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

def test_get_all_groups(db):
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())
    db.add_all([group1,group2])
    db.flush()
    db.commit()
    response = client.get("/groups")

    assert response.status_code == 200


def test_create_multiple_group_success():
    response = client.post(url="/groups",json=factories.valid_multiple_groups,headers=factories.authheader(factories.valid_admin_user))
    assert response.status_code==200

# vote
def test_vote(db):
    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())

    db.add_all([group1,group2])
    db.flush()
    db.commit()

    events = []

    # 公演作成
    for i, group in enumerate([group1, group2]):
        event_create = schemas.EventCreate(
                eventname='テスト公演',
                target='everyone',
                ticket_stock=20,
                starts_at=datetime.datetime.today() + datetime.timedelta(days=1 + i),
                ends_at=datetime.datetime.today() + datetime.timedelta(days=2 + i),
                sell_starts=datetime.datetime.today() + datetime.timedelta(days=-1),
                sell_ends=datetime.datetime.today() + datetime.timedelta(hours=1)
            )
        event = crud.create_event(db, group.id, event_create)
        events.append(event)

    # チケット取得
    db_ticket_1 = models.Ticket(id=ulid.new().str,group_id=group1.id,event_id=events[0].id, owner_id=factories.valid_guest_user['oid'], person=1, status="active",created_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9))).isoformat())
    db.add(db_ticket_1)
    db.commit()
    db.refresh(db_ticket_1)
    db_ticket_2 = models.Ticket(id=ulid.new().str,group_id=group1.id,event_id=events[1].id, owner_id=factories.valid_guest_user['oid'], person=1, status="active",created_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9))).isoformat())
    db.add(db_ticket_2)
    db.commit()
    db.refresh(db_ticket_2)

    # 投票
    response_1 = client.post(url="/votes", json=["28r", "17r"], headers=factories.authheader(factories.valid_guest_user))
    assert response_1.status_code == 200

    response_2 = client.post(url="/votes", json=["28r", "17r"], headers=factories.authheader(factories.valid_guest_user))
    assert response_2.status_code == 400

    response_3 = client.get(url=f"/votes/{group1.id}", headers=factories.authheader(factories.valid_admin_user))
    assert response_3.status_code == 200
    assert response_3.json() == {"group_id": "28r", "votes_num": 1}

#もっと細かく書けるかも(https://nmomos.com/tips/2021/03/07/fastapi-docker-8/#toc_id_2)
