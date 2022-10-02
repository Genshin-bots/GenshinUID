import platform
from pathlib import Path
from typing import Any, Set, Dict, Callable

from quart import Quart
from nonebot import get_bot
from fastapi import FastAPI, Request
import fastapi_amis_admin  # noqa: F401
from fastapi_amis_admin import amis, admin
from sqlalchemy.ext.asyncio import AsyncEngine
from fastapi_user_auth.site import AuthAdminSite
from fastapi.middleware.cors import CORSMiddleware
from fastapi_amis_admin.admin.settings import Settings
from fastapi_user_auth.auth.models import UserRoleLink
from fastapi_amis_admin.admin.site import DocsAdmin, ReDocsAdmin
from fastapi_amis_admin.amis.components import (
    App,
    Page,
    Alert,
    Property,
    PageSchema,
)

from . import login_page  # noqa: F401
from ..version import GenshinUID_version
from ..utils.db_operation.database.db_config import DATABASE_URL
from ..utils.db_operation.database.models import (
    Config,
    UidData,
    PushData,
    CookiesCache,
    NewCookiesTable,
)


class FastApiMiddleware:
    def __init__(self, app: Quart, fastapi: FastAPI, routes: Set[str]) -> None:
        self.fastapi = fastapi
        self.app = app.asgi_app
        self.routes = routes

    async def __call__(
        self, scope: Dict[str, Any], receive: Callable, send: Callable
    ) -> None:
        if scope["type"] in ("http", "websocket"):
            for path in self.routes:
                if scope["path"].startswith(path):
                    return await self.fastapi(scope, receive, send)
            return await self.app(scope, receive, send)


# 自定义后台管理站点
class GenshinUIDAdminSite(AuthAdminSite):
    template_name = str(Path(__file__).parent / 'genshinuid.html')

    def __init__(
        self,
        settings: Settings,
        fastapi: FastAPI = None,  # type: ignore
        engine: AsyncEngine = None,  # type: ignore
    ):
        super().__init__(settings, fastapi, engine)
        # 取消注册默认管理类
        self.unregister_admin(DocsAdmin, ReDocsAdmin)
        self.unregister_admin(admin.HomeAdmin)

    async def get_page(self, request: Request) -> App:
        app = await super().get_page(request)
        app.brandName = 'GenshinUID'
        app.logo = 'https://s2.loli.net/2022/01/31/kwCIl3cF1Z2GxnR.png'
        return app


# 创建FastAPI应用
app = FastAPI()
settings = Settings(  # type: ignore
    database_url_async=DATABASE_URL,
    root_path="/genshinuid",
    # logger=logger,
    site_title="GenshinUID - FastAPI Amis Admin",
)
quart = get_bot().server_app
quart.asgi_app = FastApiMiddleware(quart, app, {"/genshinuid"})

# 创建AdminSite实例
site = GenshinUIDAdminSite(settings)
auth = site.auth
config = get_bot().config

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f'http://{config.HOST}:{config:PORT}/genshinuid'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@site.register_admin
class UserAuth(admin.ModelAdmin):
    pk_name = 'user_id'
    page_schema = '用户授权'

    # 配置管理模型
    model = UserRoleLink

    async def has_page_permission(self, request: Request) -> bool:
        return await auth.requires(roles='admin', response=False)(request)


@site.register_admin
class CKadmin(admin.ModelAdmin):
    pk_name = 'UID'
    page_schema = 'CK管理'

    # 配置管理模型
    model = NewCookiesTable

    async def has_page_permission(self, request: Request) -> bool:
        return await auth.requires(roles='admin', response=False)(request)


@site.register_admin
class Configadmin(admin.ModelAdmin):
    pk_name = 'Name'
    page_schema = '配置项管理'

    # 配置管理模型
    model = Config

    async def has_page_permission(self, request: Request) -> bool:
        return await auth.requires(roles='admin', response=False)(request)


@site.register_admin
class pushadmin(admin.ModelAdmin):
    pk_name = 'UID'
    page_schema = '推送管理'

    # 配置管理模型
    model = PushData

    async def has_page_permission(self, request: Request) -> bool:
        return await auth.requires(roles='admin', response=False)(request)


@site.register_admin
class cacheadmin(admin.ModelAdmin):
    pk_name = 'UID'
    page_schema = '缓存管理'

    # 配置管理模型
    model = CookiesCache

    async def has_page_permission(self, request: Request) -> bool:
        return await auth.requires(roles='admin', response=False)(request)


@site.register_admin
class bindadmin(admin.ModelAdmin):
    pk_name = 'USERID'
    page_schema = '绑定管理'

    # 配置管理模型
    model = UidData

    async def has_page_permission(self, request: Request) -> bool:
        return await auth.requires(roles='admin', response=False)(request)


# 注册管理类
@site.register_admin
class GitHubIframeAdmin(admin.IframeAdmin):
    # 设置页面菜单信息
    page_schema = PageSchema(  # type: ignore
        label='安装Wiki', icon='fa fa-github'
    )
    # 设置跳转链接
    src = 'https://github.com/KimigaiiWuyi/GenshinUID/wiki'


# 注册自定义首页
@site.register_admin
class MyHomeAdmin(admin.HomeAdmin):
    group_schema = None
    page_schema = PageSchema(
        label=('主页'),
        icon='fa fa-home',
        url='/home',
        isDefaultPage=True,
        sort=100,
    )  # type: ignore
    page_path = '/home'

    async def get_page(self, request: Request) -> Page:
        page = await super().get_page(request)
        page.body = [
            Alert(
                level='warning',
                body=' 警告: 初始admin账号请务必前往「用户授权」➡「用户管理」处修改密码!',
            ),
            amis.Divider(),
            Property(
                title='GenshinUID Info',
                column=4,
                items=[
                    Property.Item(label='system', content=platform.system()),
                    Property.Item(
                        label='python', content=platform.python_version()
                    ),
                    Property.Item(label='version', content=GenshinUID_version),
                    Property.Item(label='license', content='GPLv3'),
                ],
            ),
        ]
        return page


# 挂载后台管理系统
site.mount_app(app)
