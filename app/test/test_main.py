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
        "description": "日比谷高校オンライン整理券システム「QUAINT」のAPI",
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
    db_ticket = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="active",
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)

    response = client.get(
        "/users/me/tickets", headers=factories.authheader(factories.valid_student_user)
    )

    assert response.status_code == 200


def test_get_is_parent_belong_to_correct():
    response = client.get(
        f"/users/me/family/belong/{factories.group1.id}",
        headers=factories.authheader(factories.valid_parent_user_28r),
    )
    assert response.json() == True


def test_get_is_parent_belong_to_incorrect():
    response = client.get(
        f"/users/me/family/belong/{factories.group1.id}",
        headers=factories.authheader(factories.valid_parent_user_11r),
    )
    assert response.json() == False


# もっと詳しくやる必要あり
def test_user_me_owner_of():
    response = client.get(
        "/users/me/owner_of", headers=factories.authheader(factories.valid_admin_user)
    )

    assert response.status_code == 200


def test_users_owner_of():
    response = client.get(
        "/users/owner_of", headers=factories.authheader(factories.valid_admin_user)
    )
    assert response.status_code == 200


# groups test
def test_get_all_groups(db):
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())
    db.add_all([group1, group2])
    db.flush()
    db.commit()
    response = client.get("/groups")

    assert response.status_code == 200


def test_create_single_group():
    response = client.post(
        "/groups",
        json=factories.valid_single_group,
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response.status_code == 200


def test_create_multiple_group_success():
    response = client.post(
        url="/groups",
        json=factories.valid_multiple_groups,
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response.status_code == 200


def test_get_group_information(db):
    crud.create_group(db, factories.group1)
    response = client.get(f"/groups/{factories.group1.id}")
    assert response.status_code == 200


def test_update_group(db):
    crud.create_group(db, factories.group1)
    crud.create_group(db, factories.group2)

    response_1 = client.put(
        f"/groups/{factories.group1.id}",
        json=factories.valid_update_group,
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response_1.status_code == 200

    response_2 = client.put(
        f"/groups/{factories.group2.id}",
        json=factories.valid_update_group,
        headers=factories.authheader(factories.valid_chief_user),
    )
    assert response_2.status_code == 200

    response_3 = client.put(
        f"/groups/{factories.group1.id}",
        json=factories.valid_update_group,
        headers=factories.authheader(factories.valid_student_user),
    )
    assert response_3.status_code == 401
    assert response_3.json() == {
        "detail": "Admin・当該GroupのOwner・チーフのいずれかの権限が必要です"
    }


def test_delete_group(db):
    crud.create_group(db, factories.group1)
    response = client.delete(
        f"/groups/{factories.group1.id}",
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response.status_code == 200


def test_create_group_tag(db):
    crud.create_group(db, factories.group1)

    # create tag
    db_tag = models.Tag(id="test_tag_id", tagname="test")

    response_404 = client.put(
        f"/groups/{factories.group1.id}/tags",
        json={"tag_id": db_tag.id},
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response_404.status_code == 404

    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    response_200 = client.put(
        f"/groups/{factories.group1.id}/tags",
        json={"tag_id": db_tag.id},
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response_200.status_code == 200


def test_delete_group_tag(db):
    crud.create_group(db, factories.group1)
    db_tag = models.Tag(id="test", tagname="test_tag")
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    crud.add_tag(db, factories.group1.id, factories.group_tag_create1)

    response = client.delete(
        f"/groups/{factories.group1.id}/tags/{factories.group_tag_create1.tag_id}",
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response.status_code == 200


def test_get_group_links(db):
    crud.create_group(db, factories.group1)
    crud.add_grouplink(db, factories.group1.id, "https://x.com/", "twitter")

    response = client.get(f"/groups/{factories.group1.id}/links")
    response.status_code == 200


def test_add_and_delete_grouplinks(db):
    crud.create_group(db, factories.group1)
    crud.create_group(db, factories.group2)

    # adminによる追加
    response_1 = client.post(
        f"/groups/{factories.group1.id}/links",
        json={"linktext": "https://x.com/TokyoHibiyaHS", "name": "テスト用リンク１"},
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response_1.status_code == 200

    # chiefによる追加
    response_2 = client.post(
        f"/groups/{factories.group2.id}/links",
        json={"linktext": "https://x.com/TokyoHibiyaHS", "name": "テスト用リンク１"},
        headers=factories.authheader(factories.valid_chief_user),
    )
    assert response_2.status_code == 200

    # adminによる削除
    response_3 = client.delete(
        f"/groups/{factories.group1.id}/links/" + response_1.json()["id"],
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response_3.status_code == 200

    # chiefによる削除
    response_4 = client.delete(
        f"/groups/{factories.group2.id}/links/" + response_2.json()["id"],
        headers=factories.authheader(factories.valid_chief_user),
    )
    assert response_4.status_code == 200


### events
def test_count_tickets(db):
    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=2),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(minutes=-10),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=10),
    )
    event = crud.create_event(db, group1.id, event_create)

    # activeなチケットを作成
    ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="active",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_1)
    db.commit()
    db.refresh(ticket_1)

    ticket_2 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="used",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_2)
    db.commit()
    db.refresh(ticket_2)

    ticket_3 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="cancelled",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_3)
    db.commit()
    db.refresh(ticket_3)

    response = client.get(f"/groups/{group1.id}/events/{event.id}/tickets")
    assert response.json() == {"taken_tickets": 2, "left_tickets": 18, "stock": 20}


def test_get_all_active_tickets_of_event(db):
    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=2),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(minutes=-10),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=10),
    )
    event = crud.create_event(db, group1.id, event_create)

    # activeなチケットを作成
    ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="active",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_1)
    db.commit()
    db.refresh(ticket_1)

    ticket_2 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="active",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_2)
    db.commit()
    db.refresh(ticket_2)

    ticket_3 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="cancelled",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_3)
    db.commit()
    db.refresh(ticket_3)

    res = client.get(
        f"/groups/{group1.id}/events/{event.id}/tickets/active",
        headers=factories.authheader(factories.valid_student_user),
    )
    assert res.json() == [ticket_1.id, ticket_2.id]

    invalid_user_res = client.get(
        f"/groups/{group1.id}/events/{event.id}/tickets/active",
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert invalid_user_res.status_code != 200


### tickets
def test_create_ticket_used_qualified(db):

    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=2),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(minutes=-10),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=10),
    )
    event = crud.create_event(db, group1.id, event_create)

    # activeなチケットを作成
    ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="used",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_1)
    db.commit()
    db.refresh(ticket_1)

    res = client.post(
        f"/groups/{group1.id}/events/{event.id}/tickets",
        params={"person": 1},
        headers=factories.authheader(factories.valid_student_user),
    )
    assert res.json() == {
        "detail": "既にこの公演・この公演と重複する時間帯の公演の整理券を取得している場合、新たに取得はできません。または取得できる整理券の枚数の上限を超えています"
    }


# create ticket for admin
def test_create_ticket_admin(db):
    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=2,
        starts_at=datetime.now(timezone(timedelta(hours=+10)))
        + timedelta(days=2),  # 優先券以外では取得不可の時間設定
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=+1, hours=+0),
        sell_ends=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=+1, hours=+1),
    )
    event = crud.create_event(db, group1.id, event_create)

    response_1 = client.post(
        f"/groups/{group1.id}/events/{event.id}/tickets/admin",
        params={"person": 1},
        headers=factories.authheader(factories.valid_admin_user),
    )
    response_2 = client.post(
        f"/groups/{group1.id}/events/{event.id}/tickets/admin",
        params={"person": 1},
        headers=factories.authheader(factories.valid_admin_user),
    )
    response_3 = client.post(
        f"/groups/{group1.id}/events/{event.id}/tickets/admin",
        params={"person": 1},
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_3.status_code == 404


def test_create_family_ticket(db):
    # 環境変数書き換え
    # テスト実行後に変数は元の値に戻してくれるみたい
    settings.family_ticket_sell_starts = (
        datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=-1)
    ).isoformat()

    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())
    group3 = models.Group(
        **factories.group4.dict()
    )  # factories.group3はtypeがtestなのでgroup4

    db.add_all([group1, group2, group3])
    db.flush()
    db.commit()

    events = []

    # 公演作成
    for i, group in enumerate([group1, group2, group3]):
        event_create = schemas.EventCreate(
            eventname="テスト公演",
            target="everyone",
            ticket_stock=20,
            starts_at=datetime.now(timezone(timedelta(hours=+9)))
            + timedelta(days=2 + i),  # 優先券以外では取得不可の時間設定
            ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3 + i),
            sell_starts=datetime.now(timezone(timedelta(hours=+9)))
            + timedelta(days=+1, hours=+0),
            sell_ends=datetime.now(timezone(timedelta(hours=+9)))
            + timedelta(days=+1, hours=+1),
        )
        event = crud.create_event(db, group.id, event_create)
        events.append(event)

    response_1 = client.post(
        f"/groups/{group1.id}/events/{events[0].id}/tickets/family",
        headers=factories.authheader(factories.valid_parent_user_28r),
    )
    assert response_1.status_code == 200
    response_2 = client.post(
        f"/groups/{group1.id}/events/{events[1].id}/tickets/family",
        headers=factories.authheader(factories.valid_parent_user_28r),
    )
    assert response_2.status_code == 200
    response_3 = client.post(
        f"/groups/{group1.id}/events/{events[2].id}/tickets/family",
        headers=factories.authheader(factories.valid_parent_user_28r),
    )
    assert response_3.json() == {
        "detail": "既に保護者用優先券を2枚以上取得しています。"
    }

    response_4 = client.get(
        "/users/me/tickets/family",
        headers=factories.authheader(factories.valid_parent_user_28r),
    )
    assert response_4.json() == True

    response_5 = client.get(
        "/users/me/count/tickets/family",
        headers=factories.authheader(factories.valid_parent_user_28r),
    )
    response_5.json() == 2


def test_create_family_ticket_same_event(db):
    # 環境変数書き換え
    # テスト実行後に変数は元の値に戻してくれるみたい
    settings.family_ticket_sell_starts = (
        datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=-1)
    ).isoformat()

    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+10)))
        + timedelta(days=2),  # 優先券以外では取得不可の時間設定
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=+1, hours=+0),
        sell_ends=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=+1, hours=+1),
    )
    event = crud.create_event(db, group1.id, event_create)

    response_1 = client.post(
        f"/groups/{group1.id}/events/{event.id}/tickets/family",
        headers=factories.authheader(factories.valid_parent_user_28r),
    )

    response_2 = client.post(
        f"/groups/{group1.id}/events/{event.id}/tickets/family",
        headers=factories.authheader(factories.valid_parent_user_28r),
    )

    assert response_1.status_code == 200
    assert response_2.status_code == 200


def test_create_family_ticket_wrong_time(db):
    # 環境変数書き換え
    # テスト実行後に変数は元の値に戻してくれるみたい
    settings.family_ticket_sell_starts = (
        datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1)
    ).isoformat()

    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=2),  # 優先券以外では取得不可の時間設定
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=+1, hours=+0),
        sell_ends=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=+1, hours=+1),
    )
    event = crud.create_event(db, group1.id, event_create)

    response = client.post(
        f"/groups/{group1.id}/events/{event.id}/tickets/family",
        headers=factories.authheader(factories.valid_parent_user_28r),
    )
    assert response.json() == {"detail": "現在優先券の配布時間外です"}


def test_create_family_ticket_invalid_user(db):
    # 環境変数書き換え
    # テスト実行後に変数は元の値に戻してくれるみたい
    settings.family_ticket_sell_starts = (
        datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=+1)
    ).isoformat()

    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=2),  # 優先券以外では取得不可の時間設定
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=+1, hours=+0),
        sell_ends=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(days=+1, hours=+1),
    )
    event = crud.create_event(db, group1.id, event_create)

    response_1 = client.post(
        f"/groups/{group1.id}/events/{event.id}/tickets/family",
        headers=factories.authheader(factories.valid_student_user),
    )
    assert response_1.status_code == 403

    response_2 = client.post(
        f"/groups/{group1.id}/events/{event.id}/tickets/family",
        headers=factories.authheader(factories.valid_parent_user_12r),
    )
    assert response_2.json() == {
        "detail": "アカウントが指定された団体に保護者として登録されていません。"
    }


def test_change_ticket_used(db):
    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=2),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(minutes=-10),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=10),
    )
    event = crud.create_event(db, group1.id, event_create)

    # activeなチケットを作成
    ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="active",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_1)
    db.commit()
    db.refresh(ticket_1)

    # キャンセル状態のチケットを作成
    ticket_2 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="cancelled",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_2)
    db.commit()
    db.refresh(ticket_2)

    # usedのチケットを作成
    ticket_3 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="used",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_3)
    db.commit()
    db.refresh(ticket_3)

    response_1 = client.put(
        f"/tickets/{ticket_1.id}",
        headers=factories.authheader(factories.valid_student_user),
    )
    response_2 = client.put(
        f"/tickets/{ticket_2.id}",
        headers=factories.authheader(factories.valid_student_user),
    )
    response_3 = client.put(
        f"/tickets/{ticket_3.id}",
        headers=factories.authheader(factories.valid_student_user),
    )

    assert response_1.status_code == 200
    assert response_2.status_code == 404
    assert response_3.status_code == 404


def test_check_ticket_available(db):
    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    # 公演作成
    event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=2),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=3),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(minutes=-10),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=10),
    )
    event = crud.create_event(db, group1.id, event_create)

    # activeなチケットを作成
    ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="active",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_1)
    db.commit()
    db.refresh(ticket_1)

    # キャンセル状態のチケットを作成
    ticket_2 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="cancelled",
        is_family_ticket=False,
        created_at=datetime.now(timezone(timedelta(hours=+9))).isoformat(),
    )
    db.add(ticket_2)
    db.commit()
    db.refresh(ticket_2)

    response_1 = client.get(
        f"/tickets/{ticket_1.id}/available",
        headers=factories.authheader(factories.valid_student_user),
    )
    assert response_1.json() == True

    response_2 = client.get(
        f"/tickets/{ticket_2.id}/available",
        headers=factories.authheader(factories.valid_student_user),
    )
    assert response_2.json() == False

    response_3 = client.get(
        f"/tickets/aaaaaaaaaaaa/available",
        headers=factories.authheader(factories.valid_student_user),
    )
    assert response_3.json() == False


# vote
# voteの作成・カウント
def test_vote(db):
    # 団体作成
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())
    group3 = models.Group(**factories.group5.dict())
    group4 = models.Group(**factories.group6.dict())

    db.add_all([group1, group2, group3, group4])
    db.flush()
    db.commit()

    events = []

    # 公演作成
    group1_event = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-1),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-30),
        sell_starts=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=-1),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-4),
    )
    events.append(crud.create_event(db, group1.id, group1_event))

    group2_event = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-2),
        ends_at=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(hours=-1, minutes=-30),
        sell_starts=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=-1),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-4),
    )
    events.append(crud.create_event(db, group2.id, group2_event))

    group3_event = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-3),
        ends_at=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(hours=-2, minutes=-30),
        sell_starts=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=-1),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-4),
    )
    events.append(crud.create_event(db, group3.id, group3_event))

    # 演劇がまだ終わっていない -> 投票不可
    group4_event = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=+30),
        sell_starts=datetime.now(timezone(timedelta(hours=+9))) + timedelta(days=-1),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-4),
    )
    events.append(crud.create_event(db, group4.id, group4_event))

    # チケット取得
    # guest チケット作成
    db_ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=events[0].id,
        owner_id=factories.valid_guest_user["oid"],
        person=1,
        status="used",
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-5)
        ).isoformat(),
    )
    db.add(db_ticket_1)
    db.commit()
    db.refresh(db_ticket_1)
    db_ticket_2 = models.Ticket(
        id=ulid.new().str,
        group_id=group2.id,
        event_id=events[1].id,
        owner_id=factories.valid_guest_user["oid"],
        person=1,
        status="active",
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-5)
        ).isoformat(),
    )
    db.add(db_ticket_2)
    db.commit()
    db.refresh(db_ticket_2)
    db_ticket_3 = models.Ticket(
        id=ulid.new().str,
        group_id=group3.id,
        event_id=events[2].id,
        owner_id=factories.valid_guest_user["oid"],
        person=1,
        status="active",
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-5)
        ).isoformat(),
    )
    db.add(db_ticket_3)
    db.commit()
    db.refresh(db_ticket_3)
    db_ticket_4 = models.Ticket(
        id=ulid.new().str,
        group_id=group4.id,
        event_id=events[3].id,
        owner_id=factories.valid_guest_user["oid"],
        person=1,
        status="active",
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-5)
        ).isoformat(),
    )
    db.add(db_ticket_4)
    db.commit()
    db.refresh(db_ticket_4)

    # parent チケット作成
    parent_db_ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=events[0].id,
        owner_id=factories.valid_parent_user_28r["oid"],
        person=1,
        status="active",
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-5)
        ).isoformat(),
    )
    db.add(parent_db_ticket_1)
    db.commit()
    db.refresh(parent_db_ticket_1)

    # student チケット作成
    student_db_ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=events[0].id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="active",
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(hours=-5)
        ).isoformat(),
    )
    db.add(student_db_ticket_1)
    db.commit()
    db.refresh(student_db_ticket_1)

    """
    状況整理
    - guest: group1 group2 group3 の整理券を取得
    - parent: group1 の整理券を取得
    - student: group1 の整理券を取得

    group1_event ends_at -30 minutes 取得可能
    group2_event ends_at -1 hours -30 minutes 取得可能
    group3_event ends_at -2 hours -30 minutes 取得可能
    group4_event ends_at +30 minutes 取得不可
    """

    # 投票
    # 連番で変数名ずらしていくのが面倒だから　response_14 が一番上にある
    response_14 = client.post(
        url="/votes",
        params={"group_id": group4.id},
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_14.json() == {
        "detail": "すでにその団体に対して投票済みまたは有効な整理券がありません。"
    }

    # guest 一つ目 正常
    response_1 = client.post(
        url="/votes",
        params={"group_id": group1.id},
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_1.status_code == 200

    # guest validation error
    response_2 = client.post(
        url="/votes",
        json=[group1.id, group2.id],
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_2.status_code == 422

    # admin
    response_3 = client.get(
        url=f"/votes/{group1.id}",
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response_3.status_code == 200
    assert response_3.json() == {"group_id": group1.id, "votes_num": 1}

    # guest 二つ目 正常
    response_4 = client.post(
        url="/votes",
        params={"group_id": group2.id},
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_4.status_code == 200

    # guest 三つ目　エラー
    response_5 = client.post(
        url="/votes",
        params={"group_id": group3.id},
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_5.json() == {"detail": "投票は1人2回までです"}

    # parent 一つ目 正常
    response_6 = client.post(
        url="/votes",
        params={"group_id": group1.id},
        headers=factories.authheader(factories.valid_parent_user_28r),
    )
    assert response_6.status_code == 200

    # admin
    response_7 = client.get(
        url=f"/votes/{group1.id}",
        headers=factories.authheader(factories.valid_admin_user),
    )
    assert response_7.status_code == 200
    assert response_7.json() == {"group_id": group1.id, "votes_num": 2}

    # student create vote permission error
    response_8 = client.post(
        url="/votes",
        params={"group_id": group1.id},
        headers=factories.authheader(factories.valid_student_user),
    )
    assert response_8.json() == {"detail": "ゲストまたは保護者である必要があります"}

    response_9 = client.get(
        url=f"/users/me/votes/{group1.id}",
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_9.json() == False

    response_10 = client.get(
        url=f"/users/me/votes/{group2.id}",
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_10.json() == False

    response_11 = client.get(
        url="/users/me/count/votes",
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_11.json() == 2

    response_12 = client.get(
        url=f"/votes/{group1.id}",
        headers=factories.authheader(factories.valid_chief_user),
    )
    assert response_12.status_code == 200
    assert response_12.json() == {"group_id": group1.id, "votes_num": 2}

    response_13 = client.get(
        url=f"/votes/{group1.id}",
        headers=factories.authheader(factories.valid_student_user),
    )
    assert response_13.json() == {"detail": "Adminまたはchiefである必要があります"}


# userが投票可能か
def test_get_user_votable(db):
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())

    db.add_all([group1, group2])
    db.flush()
    db.commit()

    vote_1 = models.Vote(
        id=ulid.new().str, group_id=group1.id, user_id=factories.valid_guest_user["oid"]
    )
    db.add(vote_1)
    db.commit()
    db.refresh(vote_1)

    response_1 = client.get(
        url="/users/me/votable",
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_1.json() == True

    vote_2 = models.Vote(
        id=ulid.new().str, group_id=group2.id, user_id=factories.valid_guest_user["oid"]
    )
    db.add(vote_2)
    db.commit()
    db.refresh(vote_2)

    response_2 = client.get(
        url="/users/me/votable",
        headers=factories.authheader(factories.valid_guest_user),
    )
    assert response_2.json() == False


# userの投票情報を取得
def test_get_user_votes(db):
    group1 = models.Group(**factories.group1.dict())
    group2 = models.Group(**factories.group2.dict())

    db.add_all([group1, group2])
    db.flush()
    db.commit()

    vote_1 = models.Vote(
        id=ulid.new().str, group_id=group1.id, user_id=factories.valid_guest_user["oid"]
    )
    db.add(vote_1)
    db.commit()
    db.refresh(vote_1)

    vote_2 = models.Vote(
        id=ulid.new().str, group_id=group2.id, user_id=factories.valid_guest_user["oid"]
    )
    db.add(vote_2)
    db.commit()
    db.refresh(vote_2)

    response = client.get(
        url="/users/me/votes", headers=factories.authheader(factories.valid_guest_user)
    )
    assert response.status_code == 200


### news
def test_create_news(db):
    response_1 = client.post(
        f"/news/create",
        json={"title": "admin", "author": "admin", "detail": "管理者"},
        headers=factories.authheader(factories.valid_admin_user),
    )
    response_2 = client.post(
        f"/news/create",
        json={"title": "chief", "author": "chief", "detail": "チーフ会"},
        headers=factories.authheader(factories.valid_chief_user),
    )

    assert response_1.status_code == 200
    assert response_2.status_code == 200


# もっと細かく書けるかも(https://nmomos.com/tips/2021/03/07/fastapi-docker-8/#toc_id_2)
