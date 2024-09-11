from datetime import datetime, timedelta, timezone

from app import crud, schemas, models
from app.main import app
from app.test import factories

from fastapi import HTTPException
from fastapi.testclient import TestClient
from requests import Session
from typing_extensions import assert_type
import pytest
import pandas as pd
import ulid

client = TestClient(app)

# crud.pyの関数の順番順にテストを書いていく
# 一部のテストは実装していない(特にJWTトークンが絡む部分)


def test_time_overlap():
    # 重なっている場合1
    start1 = datetime(year=2024, month=9, day=12, hour=8, minute=30)
    end1 = datetime(year=2024, month=9, day=12, hour=9, minute=30)
    start2 = datetime(year=2024, month=9, day=12, hour=8, minute=45)
    end2 = datetime(year=2024, month=9, day=12, hour=9, minute=45)
    assert crud.time_overlap(start1, end1, start2, end2) == True

    # 重なっている場合2
    start3 = datetime(year=2024, month=9, day=12, hour=8, minute=30)
    end3 = datetime(year=2024, month=9, day=12, hour=9, minute=30)
    start4 = datetime(year=2024, month=9, day=12, hour=8, minute=35)
    end4 = datetime(year=2024, month=9, day=12, hour=9, minute=25)
    assert crud.time_overlap(start3, end3, start4, end4) == True

    # 重なっている場合3
    start5 = datetime(year=2024, month=9, day=12, hour=9, minute=30)
    end5 = datetime(year=2024, month=9, day=12, hour=10, minute=30)
    start6 = datetime(year=2024, month=9, day=12, hour=8, minute=35)
    end6 = datetime(year=2024, month=9, day=12, hour=9, minute=45)
    assert crud.time_overlap(start5, end5, start6, end6) == True

    # 重なっていない場合
    start7 = datetime(year=2024, month=9, day=12, hour=8, minute=30)
    end7 = datetime(year=2024, month=9, day=12, hour=9, minute=30)
    start8 = datetime(year=2024, month=9, day=12, hour=9, minute=35)
    end8 = datetime(year=2024, month=9, day=12, hour=10, minute=25)
    assert crud.time_overlap(start7, end7, start8, end8) == False


def test_is_parent_belong_to():
    assert (
        crud.is_parent_belong_to(
            group_id="11r", user=schemas.JWTUser(**factories.valid_parent_user_11r)
        )
        == True
    )
    assert (
        crud.is_parent_belong_to(
            group_id="11r", user=schemas.JWTUser(**factories.valid_parent_user_12r)
        )
        == False
    )


def test_create_group(db):
    crud.create_group(db, factories.group1)

    # 追加したidに一致するオブジェクトが格納されている
    assert db.query(models.Group).filter(models.Group.id == factories.group1.id) != None


# これは何をテストするべき？
def test_get_all_groups_public(db):
    pass


# これは何をテストするべき？
def test_get_group_public(db):
    pass


# 改善が必要
def test_update_group(db):
    crud.create_group(db, factories.group1)
    res_group = crud.update_group(db, factories.group1, factories.group1_update)
    assert res_group != None


def test_change_public_thumbnail_image_url(db):
    crud.create_group(db, factories.group1)
    res_group = crud.change_public_thumbnail_image_url(db, factories.group1, "abcdefg")

    assert res_group.public_thumbnail_image_url == "abcdefg"


def test_add_tag(db):
    tag = factories.group_tag_create1
    db_tag = models.Tag(id=tag.tag_id, tagname="sample")
    db_group = models.Group(**factories.group1.dict())

    # テスト用のgroupをDBに追加
    db.add(db_group)
    db.add(db_tag)
    db.commit()
    db.refresh(db_group)

    # 指定された団体が存在しない
    assert crud.add_tag(db, factories.group2.id, tag) == None

    # 存在しないタグを追加
    assert (
        crud.add_tag(db, factories.group1.id, schemas.GroupTagCreate(tag_id="sample"))
        == None
    )

    # 重複していないタグを追加
    assert crud.add_tag(db, factories.group1.id, tag) != None

    # 重複しているタグを追加
    with pytest.raises(HTTPException) as err:
        crud.add_tag(db, factories.group1.id, tag)
    assert err.value.status_code == 200
    assert err.value.detail == "Already Registed"


### events
def test_event_all_tickets_active(db):
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

    assert crud.get_all_active_tickets_of_event(db, event.id) == [
        ticket_1.id,
        ticket_2.id,
    ]


def test_convert_df():
    origin_df = pd.read_csv("/workspace/csv/sample-sheet-v2.csv")
    converted_df = pd.read_csv("/workspace/csv/sample-sheet-v1.csv")

    res_df = crud.convert_df(origin_df)

    for m in range(len(origin_df)):
        for n in range(len(converted_df.columns.values)):
            assert res_df.iat[m, n] == converted_df.iat[m, n]


def test_check_df(db):
    correct_df = pd.read_csv(filepath_or_buffer="/workspace/csv/sample-sheet.csv")
    incorrect_title_df = pd.read_csv(
        filepath_or_buffer="/workspace/csv/incorrect-title-sheet.csv"
    )
    incorrect_groupid_df = pd.read_csv(
        filepath_or_buffer="/workspace/csv/incorrect-groupid-sheet.csv"
    )
    incorrect_time_df = pd.read_csv(
        filepath_or_buffer="/workspace/csv/incorrect-time-sheet.csv"
    )
    incorrect_time_start = pd.read_csv(
        filepath_or_buffer="/workspace/csv/incorrect-time-setting-start-sheet.csv"
    )
    incorrect_time_sell = pd.read_csv(
        filepath_or_buffer="/workspace/csv/incorrect-time-setting-sell-sheet.csv"
    )

    group = factories.group3
    crud.create_group(db, group)

    assert crud.check_df(db, correct_df) == None

    with pytest.raises(HTTPException) as err1:
        crud.check_df(db, incorrect_title_df)
    assert err1.value.status_code == 422

    with pytest.raises(HTTPException) as err2:
        crud.check_df(db, incorrect_groupid_df)
    assert err2.value.status_code == 400

    with pytest.raises(HTTPException) as err3:
        crud.check_df(db, incorrect_time_df)
    assert err3.value.status_code == 422

    with pytest.raises(HTTPException) as err4:
        crud.check_df(db, incorrect_time_start)
    assert err4.value.status_code == 400

    with pytest.raises(HTTPException) as err5:
        crud.check_df(db, incorrect_time_sell)
    assert err5.value.status_code == 400


def test_create_events_from_df(db):
    df = pd.read_csv(filepath_or_buffer="/workspace/csv/sample-sheet.csv")

    group = factories.group3
    crud.create_group(db, group)

    assert crud.create_events_from_df(db, df) == None


### tickets
def test_use_ticket(db):
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
    ticket_1 = crud.create_ticket(
        db, event, schemas.JWTUser(**factories.valid_student_user), 1
    )

    assert crud.use_ticket(db, ticket_1.id).status == "used"
    assert crud.use_ticket(db, "aaaa") == None


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
    ticket_1 = crud.create_ticket(
        db, event, schemas.JWTUser(**factories.valid_student_user), 1
    )

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

    # キャンセル状態のチケットを作成
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

    assert crud.check_ticket_available(db, ticket_1.id) == True
    # 存在しないチケットを参照
    assert crud.check_ticket_available(db, "aaaaaaaa") == False
    assert crud.check_ticket_available(db, ticket_3.id) == False


### votes
def test_get_user_votable(db):
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    group2 = models.Group(**factories.group2.dict())
    db.add(group2)
    db.commit()
    db.refresh(group2)

    # 公演作成
    group1_event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-30),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-10),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(minutes=-50),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-40),
    )
    group1_event = crud.create_event(db, group1.id, group1_event_create)

    group2_event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-30),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-10),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(minutes=-50),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-40),
    )
    group2_event = crud.create_event(db, group2.id, group2_event_create)

    # activeなチケットを作成
    ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=group1_event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="active",
        is_family_ticket=False,
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-45)
        ).isoformat(),
    )
    db.add(ticket_1)
    db.commit()
    db.refresh(ticket_1)

    # used状態のチケットを作成
    ticket_2 = models.Ticket(
        id=ulid.new().str,
        group_id=group2.id,
        event_id=group2_event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="used",
        is_family_ticket=False,
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-45)
        ).isoformat(),
    )
    db.add(ticket_2)
    db.commit()
    db.refresh(ticket_2)

    assert (
        crud.get_user_votable(
            db, schemas.JWTUser(**factories.valid_student_user), group1.id
        )
        == True
    )
    assert (
        crud.get_user_votable(
            db, schemas.JWTUser(**factories.valid_student_user), group2.id
        )
        == True
    )


def test_get_user_vote_count(db):
    group1 = models.Group(**factories.group1.dict())
    db.add(group1)
    db.commit()
    db.refresh(group1)

    group2 = models.Group(**factories.group2.dict())
    db.add(group2)
    db.commit()
    db.refresh(group2)

    # 公演作成
    group1_event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-30),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-10),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(minutes=-50),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-40),
    )
    group1_event = crud.create_event(db, group1.id, group1_event_create)

    group2_event_create = schemas.EventCreate(
        eventname="テスト公演",
        target="everyone",
        ticket_stock=20,
        starts_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-30),
        ends_at=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-10),
        sell_starts=datetime.now(timezone(timedelta(hours=+9)))
        + timedelta(minutes=-50),
        sell_ends=datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-40),
    )
    group2_event = crud.create_event(db, group2.id, group2_event_create)

    # activeなチケットを作成
    ticket_1 = models.Ticket(
        id=ulid.new().str,
        group_id=group1.id,
        event_id=group1_event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="active",
        is_family_ticket=False,
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-45)
        ).isoformat(),
    )
    db.add(ticket_1)
    db.commit()
    db.refresh(ticket_1)

    # used状態のチケットを作成
    ticket_2 = models.Ticket(
        id=ulid.new().str,
        group_id=group2.id,
        event_id=group2_event.id,
        owner_id=factories.valid_student_user["oid"],
        person=1,
        status="used",
        is_family_ticket=False,
        created_at=(
            datetime.now(timezone(timedelta(hours=+9))) + timedelta(minutes=-45)
        ).isoformat(),
    )
    db.add(ticket_2)
    db.commit()
    db.refresh(ticket_2)

    crud.create_vote(db, group1.id, schemas.JWTUser(**factories.valid_student_user))
    crud.create_vote(db, group2.id, schemas.JWTUser(**factories.valid_student_user))

    assert crud.get_user_vote_count(db, schemas.JWTUser(**factories.valid_student_user))
