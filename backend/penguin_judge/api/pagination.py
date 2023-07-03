from typing import Any

import sqlalchemy as sa
from fastapi import Query, Response

from penguin_judge.db import Tx

QueryPaginationPage = Query(1, title="ページ番号", ge=1)
QueryPaginationPerPage = Query(20, title="1ページ当たりのアイテム数", ge=1, le=1000)

PaginationResponseHeaders = {
    "X-Total": {"description": "全アイテム数", "schema": {"type": "integer"}},
    "X-Total-Pages": {"description": "全ページ数", "schema": {"type": "integer"}},
    "X-Per-Page": {"description": "ページ当たりのアイテム数", "schema": {"type": "integer"}},
    "X-Page": {"description": "現在のページ数 (1スタート)", "schema": {"type": "integer"}},
}


class Pagination(object):
    def __init__(
        self,
        resp: Response,
        page: int = QueryPaginationPage,
        per_page: int = QueryPaginationPerPage,
    ) -> None:
        self.page = page
        self.per_page = per_page
        self.response = resp

    async def setup(self, tx: Tx, query: Any) -> Any:
        """引数で指定されたクエリの件数を取得し、paginationを適用したクエリを返却します."""

        # 件数を取得し、レスポンスヘッダにページネーション情報を設定
        total = await tx.session.scalar(
            sa.select(sa.func.count()).select_from(query.subquery())
        )
        assert isinstance(total, int)
        self.response.headers.update(
            {
                "X-Total": str(total),
                "X-Total-Pages": str((total + self.per_page - 1) // self.per_page),
                "X-Per-Page": str(self.per_page),
                "X-Page": str(self.page),
            }
        )

        # ページネーションを適用したクエリを返却
        return query.offset((self.page - 1) * self.per_page).limit(self.per_page)
