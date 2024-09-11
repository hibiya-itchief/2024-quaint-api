import datetime
import os
from dotenv import load_dotenv

from pydantic import BaseSettings

load_dotenv()


class Parameters(BaseSettings):
    person_per_user: int = 3  # 1つのユーザーで同時入場できる人数
    max_tickets: int = 0  # 全日程を通して取得できる整理券の上限(0で制限無し)
    max_tickets_per_day: int = (
        0  # 1日あたりの取得できる整理券の上限(0で上限無し)各公演の開始時刻で判定されます
    )


class Settings(BaseSettings):
    mysql_user: str = os.getenv("MYSQL_USER")
    mysql_password: str = os.getenv("MYSQL_PASSWORD")
    db_host: str = os.getenv("DB_HOST")
    mysql_database: str = os.getenv("MYSQL_DATABASE")

    jwt_privatekey: str = os.getenv("JWT_PRIVATEKEY")
    jwt_publickey: str = (
        "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0i+BMxUUgG6slPW/9oHP\nUrYpoLX08NNTsFpEwAkpBHxzbauFc2SmFaFnmkkco8lfCQs66sj6fwtTtSc4RH+Z\nncFRaxV5M+AS7utyGhS9iNAg6u5DaGAxbMm1NAqUkuNLGS+pVx+p75b681inCBBu\nVxpPF0eCNMsUfMPDBKKKS6ABuIpl4Ep3BDXLCSfciBFixDA6poIDy7tryfcpglyw\nuq84ROrOBLU3kTaTM4zl8x2VRkGGdU88+7WhpVgB7s7uSJmzmWtojvDGp+1tylqp\nB4geNVB8rjqkZQjr9Y0oI2sJuIAYzDaBWwQsVUMmp2JO64kR8P1P7i99graUaGOd\nJwIDAQAB\n-----END PUBLIC KEY-----"
    )

    # 星陵祭の設定
    family_ticket_sell_starts: str = os.getenv("FAMILY_TICKET_SELL_STARTS")

    # Azure Blob Storage
    connect_str: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name: str = os.getenv("AZURE_BLOB_STORAGE_CONTAINER_NAME")

    # Parameter

    ## Azure Config
    azure_b2c_openidconfiguration = "https://seiryofesb2c.b2clogin.com/seiryofesb2c.onmicrosoft.com/v2.0/.well-known/openid-configuration?p=B2C_1_quaint-app"
    azure_b2c_audience = "06b8cb1b-b866-43bf-9bc6-2898c6a149f3"
    azure_ad_openidconfiguration = "https://login.microsoftonline.com/158e6d17-f3d5-4365-8428-26dfc74a9d27/v2.0/.well-known/openid-configuration"
    azure_ad_audience = "0f2252c5-62ef-4aab-af65-99a753f1c77c"

    b2c_msgraph_tenant: str = "450b2222-dcb5-471d-9657-bb4ee50acd97"
    b2c_msgraph_client: str = "06b8cb1b-b866-43bf-9bc6-2898c6a149f3"
    b2c_msgraph_secret: str = os.getenv("B2C_MSGRAPH_SECRET")

    ## Azure AD groups UUID
    azure_ad_groups_quaint_admin = "5c091517-25de-44bc-9e42-ffcb8539435c"
    azure_ad_groups_quaint_entry = "63a40184-8dab-43b4-8367-54e84ace6e2a"
    azure_ad_groups_quaint_owner = "a577d858-64bf-4815-aaf6-d893c654e92e"
    azure_ad_groups_quaint_parents = "ecd46dae-d84b-42d8-9357-ac24d480a168"
    azure_ad_groups_quaint_students = "865bb05d-cb7d-4919-b18d-8b977ec0499b"
    azure_ad_groups_quaint_teachers = "0a8ee476-cd37-4c31-bd6e-c34e750574f4"
    azure_ad_groups_quaint_chief = "67e48f08-22e0-4ec4-9674-1428aaa5c055"
    azure_ad_groups_quaint_guest = "94c45b57-680c-4b5b-a98b-d78f1fd90d71"
    # 保護者のグループ
    # 1年
    azure_ad_groups_quaint_parents_11r = "12c1a97c-3d99-4c4b-b70b-28e9c0c44652"
    azure_ad_groups_quaint_parents_12r = "59497287-931a-4c12-84d3-58406988210d"
    azure_ad_groups_quaint_parents_13r = "0ed9e48e-b2a0-4fb6-9045-a266d64a6248"
    azure_ad_groups_quaint_parents_14r = "1372ce7a-3151-4657-81f2-82ec0c75082e"
    azure_ad_groups_quaint_parents_15r = "0f860b70-ae51-4663-b69b-a7d972da9037"
    azure_ad_groups_quaint_parents_16r = "df919a87-e198-4c9a-9ee5-5c7763aa68c0"
    azure_ad_groups_quaint_parents_17r = "7487b933-88f4-4d11-b055-9eee011d917b"
    azure_ad_groups_quaint_parents_18r = "d2d27aa4-8a2e-43af-843c-aff23bc68310"
    # 2年
    azure_ad_groups_quaint_parents_21r = "5be0f149-9d15-472b-b25f-5eb874ace869"
    azure_ad_groups_quaint_parents_22r = "6fa005c2-a225-4e5b-80dd-b5b7f72fce1a"
    azure_ad_groups_quaint_parents_23r = "fdd3031f-105a-4369-ac7a-028cf00ddd91"
    azure_ad_groups_quaint_parents_24r = "c599b4e8-a5cb-4bd2-aaea-e32e1719d8d1"
    azure_ad_groups_quaint_parents_25r = "cf04417a-324b-4581-b6a6-efffe9574f66"
    azure_ad_groups_quaint_parents_26r = "94729412-e00b-4a02-9436-784b7c0f9dee"
    azure_ad_groups_quaint_parents_27r = "296d09c8-fc79-4787-845c-68abdc705771"
    azure_ad_groups_quaint_parents_28r = "c023ca3d-9618-4950-b2e2-50c064bcbe75"
    # 3年
    azure_ad_groups_quaint_parents_31r = "3d983fe1-8c30-4540-85e7-53b4ca98eab6"
    azure_ad_groups_quaint_parents_32r = "7ffec498-ceb2-487c-b017-3098fb1b0d3a"
    azure_ad_groups_quaint_parents_33r = "bcb43367-585d-44a7-9896-36d85aeeda6c"
    azure_ad_groups_quaint_parents_34r = "5a619348-a1c8-46c1-ba47-83bdeaf4c2b4"
    azure_ad_groups_quaint_parents_35r = "b591ff60-1217-4253-b948-d0801509511a"
    azure_ad_groups_quaint_parents_36r = "b912ad1e-c692-42d0-9115-74bc62a4158e"
    azure_ad_groups_quaint_parents_37r = "2fe29736-f843-4d4a-aec5-100c8804062e"
    azure_ad_groups_quaint_parents_38r = "28711a00-fca2-4fb7-90cb-5823d1feb9d6"

    ## JWT EXPIRE
    access_token_expire: datetime.timedelta = datetime.timedelta(days=10)

    production_flag: int = os.getenv("PRODUCTION_FLAG", 0)
    api_hostname: str = os.getenv("API_HOSTNAME", "DEFAULT")

    ## Cloudflare deploy hook url
    cloudflare_deploy_hook_url: str = os.getenv("CLOUDFLARE_DEPLOY_HOOK_URL", "")

    ## Redis
    redis_host: str = os.getenv("REDIS_HOST", "")

    ## Google Analytics Property ID
    ga_property_id: str = os.getenv("GA_PROPERTY_ID", "")

    class Config:
        env_file = "app/.env"
        secrets_dir = "/run/secrets"


params = Parameters()
settings = Settings()
