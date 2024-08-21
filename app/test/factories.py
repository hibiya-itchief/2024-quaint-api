import json
from typing import Dict
from factory.alchemy import SQLAlchemyModelFactory

import datetime

from app import models, schemas
from app.test.utils.overrides import TestingSessionLocal

### schemas.JWTUser
def authheader(user:Dict):
    return {'Authorization': json.dumps(user)}

valid_student_user={
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "865bb05d-cb7d-4919-b18d-8b977ec0499b", # quaint-students
    ],
    "name": "studentfortest",
    "oid": "25e3cf28-e627-4dfe-b5dd-bdcbe73117e1", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_parent_user={
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "ecd46dae-d84b-42d8-9357-ac24d480a168", # quaint-parents
    ],
    "name": "parentfortest",
    "oid": "25e3cf28-e627-4dfe-b5dd-bdcbe73117e2", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_parent_user_11r = {
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "ecd46dae-d84b-42d8-9357-ac24d480a168", # quaint-parents
        "12c1a97c-3d99-4c4b-b70b-28e9c0c44652", # 11r-parents
    ],
    "name": "11r_parent",
    "oid": "25e3cf28-e628-5afe-b5dd-bdcbe73117e0", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_parent_user_12r = {
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "ecd46dae-d84b-42d8-9357-ac24d480a168", # quaint-parents
        "59497287-931a-4c12-84d3-58406988210d", # 12r-parents
    ],
    "name": "12r_parent",
    "oid": "25e3cf28-e628-5afe-b5dd-bdcbe81217e0", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_parent_user_17r = {
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "ecd46dae-d84b-42d8-9357-ac24d480a168", # quaint-parents
        "7487b933-88f4-4d11-b055-9eee011d917b", # 17r-parents
    ],
    "name": "17r_parent",
    "oid": "16a3cf28-e628-5afe-b5dd-bdcbe81228j9", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_parent_user_21r = {
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "ecd46dae-d84b-42d8-9357-ac24d480a168", # quaint-parents
        "5be0f149-9d15-472b-b25f-5eb874ace869", # 21r-parents
    ],
    "name": "21r_parent",
    "oid": "35a4cf29-d156-5afe-b5dd-ddabe88887e1", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_parent_user_28r = {
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "ecd46dae-d84b-42d8-9357-ac24d480a168", # quaint-parents
        "c023ca3d-9618-4950-b2e2-50c064bcbe75", # 28r-parents
    ],
    "name": "28r_parent",
    "oid": "25e3cf29-d156-5afe-b5dd-bdcbe81217e0", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_parent_user_33r = {
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "ecd46dae-d84b-42d8-9357-ac24d480a168", # quaint-parents
        "bcb43367-585d-44a7-9896-36d85aeeda6c", # 33r-parents
    ],
    "name": "33r_parent",
    "oid": "95e2ca38-e628-5afe-b5dd-bdcbe13218e0", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_guest_user={
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "94c45b57-680c-4b5b-a98b-d78f1fd90d71", # quaint-guest
    ],
    "name": "guestfortest",
    "oid": "25e3cf28-e627-4dfe-b5dd-bdcbe73117e3", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_admin_user={
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "5c091517-25de-44bc-9e42-ffcb8539435c", # quaint-admin
    ],
    "name": "adminfortest",
    "oid": "25e3cf28-e627-4dfe-b5dd-bdcbe73117e4", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_chief_user={
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "67e48f08-22e0-4ec4-9674-1428aaa5c055", # quaint-chief
    ],
    "name": "chieffortest",
    "oid": "25e3cf28-e627-4dfe-b5dd-bdcbe73117e7", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

invalid_admin_user1={
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "5c091517-25de-44bc-9e42-ffcb8539435", # 1 charactor missing
    ],
    "name": "adminfortest",
    "oid": "25e3cf28-e627-4dfe-b5dd-bdcbe73117e5", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

invalid_admin_user2={
    "iss": "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0",
    "groups": [
        "invaliduuid", # 1 charactor missing
    ],
    "name": "adminfortest",
    "oid": "25e3cf28-e627-4dfe-b5dd-bdcbe73117e6", # random
    "sub": "BEGuhvmm8LkWHLxEK9TxDkVaMvK3nDGq6ak79HPGLsd", # random
}

valid_single_group=[{
    "id":"28r",
    "type":"play",
    "groupname":"2年8組",
    "title":"SING",
    "description":"ここに説明文",
    "enable_vote":True,
    "twitter_url":None,
    "instagram_url":None,
    "stream_url":None,
    "public_thumbnail_image_url":None,
    "public_page_content_url":"<html><h1>宣伝ページ</h1></html>",
    "private_page_content_url":"<html><h1>プライベート</h1></html>",
    "floor":1,
    "place":"社会科教室"
    }]

valid_multiple_groups=[
    {"id":"28r",
    "type":"play",
    "groupname":"2年8組",
    "title":"SING",
    "description":"ここに説明文",
    "enable_vote":True,
    "twitter_url":None,
    "instagram_url":None,
    "stream_url":None,
    "public_thumbnail_image_url":None,
    "public_page_content_url":"<html><h1>宣伝ページ</h1></html>",
    "private_page_content_url":"<html><h1>プライベート</h1></html>",
    "floor":1,
    "place":"社会科教室"},
    {"id":"17r",
    "groupname":"1年7組",
    "title":"hatopoppo",
    "description":"ここに説明文",
    "enable_vote":True,
    "twitter_url":None,
    "instagram_url":None,
    "stream_url":None,
    "public_thumbnail_image_url":None,
    "public_page_content_url":"<html><h1>宣伝ページ</h1></html>",
    "private_page_content_url":"<html><h1>プライベート</h1></html>",
    "floor":2,
    "place":"生徒ホール",
    "type":schemas.GroupType.play}]

valid_update_group = {
    "title":"あいうえお",
    "description":"変更",
    "floor":"2",
    "place":"科学室",
    "type":"play"
}


class tag1_TagCreateByAdmin():
    tagname="タグ1"
class tag2_TagCreateByAdmin():
    tagname="タグ2"
class group1_GroupCreateByAdmin():
    id="28r"
    groupname="2年8組"
    title="SING"
    description="ここに説明文"
    enable_vote=True
    twitter_url=None
    instagram_url=None
    stream_url=None
    public_thumbnail_image_url=None    
    public_page_content_url="<html><h1>宣伝ページ</h1></html>"
    private_page_content_url="<html><h1>プライベート</h1></html>"
    floor=1
    place="社会科教室"
class group2_GroupCreateByAdmin():
    id="18R"
    groupname="2年8組"
    title="あああああ"
    description="ここに説明文"
    enable_vote=False
    twitter_url=None
    instagram_url=None
    stream_url=None
    public_thumbnail_image_url=None
    public_page_content_url="<html><h1>宣伝ページ</h1></html>"
    private_page_content_url="<html><h1>プライベート</h1></html>"
    cover_image_url=None
    floor=2
    place="生徒ホール"

class Timetable():
    timetablename:str
    sell_at:datetime
    sell_ends:datetime
    starts_at:datetime
    ends_at:datetime
class valid_timetable1(Timetable):
    timetablename="1日目 - 第1公演"
    sell_at=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=0,second=0))
    sell_ends=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=30,second=0))
    starts_at=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=30,second=0))
    ends_at=str(datetime.datetime(year=2022,month=9,day=17,hour=10,minute=30,second=0))
class valid_timetable2(Timetable):
    timetablename="1日目 - 第2公演"
    sell_at=str(datetime.datetime(year=2022,month=9,day=17,hour=10,minute=0,second=0))
    sell_ends=str(datetime.datetime(year=2022,month=9,day=17,hour=10,minute=30,second=0))
    starts_at=str(datetime.datetime(year=2022,month=9,day=17,hour=10,minute=30,second=0))
    ends_at=str(datetime.datetime(year=2022,month=9,day=17,hour=11,minute=30,second=0))

class invalid_timetable1():
    timetablename="1日目 - 第1公演"
    sell_at=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=30,second=0))
    sell_ends=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=0,second=0))
    starts_at=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=30,second=0))
    ends_at=str(datetime.datetime(year=2022,month=9,day=17,hour=10,minute=30,second=0))

class invalid_timetable2():
    timetablename="1日目 - 第1公演"
    sell_at=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=0,second=0))
    sell_ends=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=30,second=0))
    starts_at=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=20,second=0))
    ends_at=str(datetime.datetime(year=2022,month=9,day=17,hour=10,minute=30,second=0))

class invalid_timetable3():
    timetablename="1日目 - 第1公演"
    sell_at=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=0,second=0))
    sell_ends=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=30,second=0))
    starts_at=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=30,second=0))
    ends_at=str(datetime.datetime(year=2022,month=9,day=17,hour=9,minute=0,second=0))

# 変数
group1 = schemas.GroupCreate(
    id="28r",
    groupname="2年8組",
    title="SING",
    description="ここに説明文",
    enable_vote=True,
    twitter_url=None,
    instagram_url=None,
    stream_url=None,
    public_thumbnail_image_url=None,
    public_page_content_url="<html><h1>宣伝ページ</h1></html>",
    private_page_content_url="<html><h1>プライベート</h1></html>",
    floor=1,
    place="社会科教室",
    type=schemas.GroupType.play
)

group2 = schemas.GroupCreate(
    id="17r",
    groupname="1年7組",
    title="hatopoppo",
    description="ここに説明文",
    enable_vote=True,
    twitter_url=None,
    instagram_url=None,
    stream_url=None,
    public_thumbnail_image_url=None,
    public_page_content_url="<html><h1>宣伝ページ</h1></html>",
    private_page_content_url="<html><h1>プライベート</h1></html>",
    floor=2,
    place="生徒ホール",
    type=schemas.GroupType.play
)

group4 = schemas.GroupCreate(
    id="33r",
    groupname="33r",
    title="hatopoppo",
    description="ここに説明文",
    enable_vote=True,
    twitter_url=None,
    instagram_url=None,
    stream_url=None,
    public_thumbnail_image_url=None,
    public_page_content_url="<html><h1>宣伝ページ</h1></html>",
    private_page_content_url="<html><h1>プライベート</h1></html>",
    floor=4,
    place="33r",
    type=schemas.GroupType.play
)

group5 = schemas.GroupCreate(
    id="11r",
    groupname="1年1組",
    title="hatopoppo",
    description="ここに説明文",
    enable_vote=True,
    twitter_url=None,
    instagram_url=None,
    stream_url=None,
    public_thumbnail_image_url=None,
    public_page_content_url="<html><h1>宣伝ページ</h1></html>",
    private_page_content_url="<html><h1>プライベート</h1></html>",
    floor=3,
    place="11r",
    type=schemas.GroupType.play
)

group6 = schemas.GroupCreate(
    id="21r",
    groupname="2年1組",
    title="hatopoppo",
    description="ここに説明文",
    enable_vote=True,
    twitter_url=None,
    instagram_url=None,
    stream_url=None,
    public_thumbnail_image_url=None,
    public_page_content_url="<html><h1>宣伝ページ</h1></html>",
    private_page_content_url="<html><h1>プライベート</h1></html>",
    floor=2,
    place="21r",
    type=schemas.GroupType.play
)

# 変数
# テストグループ
group3 = schemas.GroupCreate(
    id="test_1",
    groupname="テストグループ",
    title="TEST_TEST",
    description="TESTです",
    enable_vote=True,
    twitter_url=None,
    instagram_url=None,
    stream_url=None,
    public_thumbnail_image_url=None,
    public_page_content_url="<html><h1>宣伝ページ</h1></html>",
    private_page_content_url="<html><h1>プライベート</h1></html>",
    floor=4,
    place="LL教室",
    type=schemas.GroupType.test
)

club_1 = schemas.GroupCreate(
    id="soccer_club",
    groupname="テストグループ",
    title="TEST_TEST",
    description="TESTです",
    enable_vote=False,
    twitter_url=None,
    instagram_url=None,
    stream_url=None,
    public_thumbnail_image_url=None,
    public_page_content_url="<html><h1>宣伝ページ</h1></html>",
    private_page_content_url="<html><h1>プライベート</h1></html>",
    floor=4,
    place="LL教室",
    type=schemas.GroupType.club
)

group1_update = schemas.GroupUpdate(
    id="28r",
    groupname="2年8組",
    title="sample",
    description="ここに説明文",
    enable_vote=True,
    twitter_url=None,
    instagram_url=None,
    stream_url=None,
    public_thumbnail_image_url=None,
    public_page_content_url="<html><h1>宣伝ページ</h1></html>",
    private_page_content_url="<html><h1>プライベート</h1></html>",
    floor=3,
    place="生徒ホール",
    type=schemas.GroupType.play
)

group_tag_create1 = schemas.GroupTagCreate(
    tag_id='test'
)

# event
group1_event = schemas.EventCreate(
    eventname='一日目第一公演',
    lottery=False,
    target=schemas.UserRole.everyone,
    ticket_stock=20,
    starts_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9))) + datetime.timedelta(days=1),
    ends_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9))) + datetime.timedelta(days=2),
    sell_starts=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9))) + datetime.timedelta(days=-1),
    sell_ends=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9))) + datetime.timedelta(hours=1)
)

# tag
tag_1 = schemas.TagCreate(
    tagname='test'
)