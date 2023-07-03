import pickle
from typing import Any, Callable

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from zstandard import ZstdCompressor, ZstdDecompressor

from penguin_judge import config
from penguin_judge import models as m
from penguin_judge.api import schemas
from penguin_judge.api.auth import Claims, require_token, require_token_by_config
from penguin_judge.api.pagination import Pagination, PaginationResponseHeaders
from penguin_judge.db import Tx, start_transaction
from penguin_judge.mq import JUDGE_QUEUE_NAME, connect_mq
from penguin_judge.utils import to_fastapi_response_compatible_value

router = APIRouter()


@router.get(
    "",
    responses={200: {"headers": PaginationResponseHeaders}},
    response_model=list[schemas.SubmissionSummary],
    response_model_exclude_none=True,
)
async def list_submissions(
    contest_id: str,
    pagination: Pagination = Depends(Pagination),
    problem_id: str | None = None,
    environment_id: int | None = None,
    status: schemas.JudgeStatus | None = None,
    user_name: str | None = None,
    claims: Claims | None = Depends(require_token_by_config),
    tx: Tx = Depends(start_transaction),
) -> Any:
    contest = await tx.session.scalar(
        sa.select(m.Contest).where(m.Contest.id == contest_id)
    )
    if not (contest and contest.is_accessible(claims)):
        raise HTTPException(status_code=404)
    if not (contest.is_begun() or (claims and claims.admin)):
        raise HTTPException(status_code=403)

    q = sa.select(*m.Submission.summary_fields(), m.User.name).where(
        sa.and_(
            m.Submission.contest_id == contest_id, m.Submission.user_id == m.User.id
        )
    )
    if not (contest.is_finished() or (claims and claims.admin)):
        if not claims:
            # 未ログイン時は開催中コンテストの投稿一覧は見えない
            raise HTTPException(status_code=403)
        # コンテスト開催中は自分の投稿のみが見える
        q = q.where(m.Submission.user_id == claims.id)

    filters: list[tuple[Any, Callable[[Any], Any]]] = [
        (problem_id, m.Submission.problem_id.__eq__),
        (environment_id, m.Submission.environment_id.__eq__),
        (status, m.Submission.status.__eq__),
        (user_name, m.User.name.contains),
    ]
    for v, expr in filters:
        if v is None:
            continue
        q = q.where(expr(v))

    q = await pagination.setup(tx, q)

    ret = []
    async for row in (await tx.session.stream(q)).mappings():
        tmp = {k: to_fastapi_response_compatible_value(v) for k, v in dict(row).items()}
        del tmp["name"]
        tmp["user_name"] = row.name
        ret.append(tmp)

    return ret


@router.post("", status_code=201)
async def post_submission(
    contest_id: str,
    body: schemas.SubmissionPost,
    claims: Claims = Depends(require_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    cctx = ZstdCompressor()
    code_encoded = body.code.encode("utf8")
    code_compressed = cctx.compress(code_encoded)

    if not await tx.session.scalar(
        sa.select(sa.func.count(m.Contest.id)).where(m.Contest.id == contest_id)
    ):
        raise HTTPException(status_code=404)  # contest_idはURLに含まれるため404
    if (
        not await tx.session.scalar(
            sa.select(sa.func.count(m.Problem.id)).where(
                sa.and_(
                    m.Problem.contest_id == contest_id, m.Problem.id == body.problem_id
                )
            )
        )
    ) or (
        not await tx.session.scalar(
            sa.select(sa.func.count(m.Environment.id)).where(
                m.Environment.id == body.environment_id
            )
        )
    ):
        raise HTTPException(status_code=400)  # bodyが不正なので400

    queued_submission_count = await tx.session.scalar(
        sa.select(sa.func.count(m.Submission.id)).where(
            sa.and_(
                m.Submission.user_id == claims.id,
                m.Submission.status.in_([m.JudgeStatus.Waiting, m.JudgeStatus.Running]),
            )
        )
    )
    assert isinstance(queued_submission_count, int)
    if queued_submission_count > config.user_judge_queue_limit:
        raise HTTPException(status_code=429)

    insert_ret = await tx.session.execute(
        sa.insert(m.Submission).values(
            contest_id=contest_id,
            problem_id=body.problem_id,
            user_id=claims.id,
            code=code_compressed,
            code_bytes=len(code_encoded),
            environment_id=body.environment_id,
        )
    )
    inserted_pk = insert_ret.inserted_primary_key[0]  # type: ignore

    submission = await tx.session.scalar(
        sa.select(m.Submission).where(m.Submission.id == inserted_pk)
    )
    assert submission
    ret = submission.to_summary_dict()
    ret["user_name"] = claims.name
    await tx.commit()

    async with connect_mq() as (conn, ch):
        await ch.queue_declare(JUDGE_QUEUE_NAME)
        await ch.basic_publish(
            exchange="",
            routing_key=JUDGE_QUEUE_NAME,
            body=pickle.dumps((contest_id, body.problem_id, ret["id"])),
        )

    return ret


@router.get("/{submission_id}")
async def get_submission(
    contest_id: str,
    submission_id: int,
    claims: Claims | None = Depends(require_token_by_config),
    tx: Tx = Depends(start_transaction),
) -> Any:
    contest = await tx.session.scalar(
        sa.select(m.Contest).where(m.Contest.id == contest_id)
    )
    if not (contest and contest.is_accessible(claims)):
        raise HTTPException(status_code=404)
    tmp = await (
        await tx.session.stream(
            sa.select(m.Submission, m.User.name).where(
                sa.and_(
                    m.Submission.contest_id == contest_id,
                    m.Submission.id == submission_id,
                    m.Submission.user_id == m.User.id,
                )
            )
        )
    ).first()
    if not tmp:
        raise HTTPException(status_code=404)

    submission, user_name = tmp
    if not submission.is_accessible(contest, claims):
        raise HTTPException(status_code=404)

    zctx = ZstdDecompressor()
    ret = submission.to_dict()
    ret["code"] = zctx.decompress(submission.code).decode("utf-8")
    ret["user_name"] = user_name
    ret["tests"] = []

    q = (
        sa.select(m.JudgeResult)
        .where(m.JudgeResult.submission_id == submission_id)
        .order_by(m.JudgeResult.status, m.JudgeResult.test_id)
    )
    async for row in await tx.session.stream_scalars(q):
        t = row.to_dict()

        # 不要な情報を削除
        t.pop("contest_id")
        t.pop("problem_id")
        t.pop("submission_id")

        t["id"] = t["test_id"]
        t.pop("test_id")
        if not (contest.is_finished() or (claims and claims.admin)):
            # コンテスト中＆非管理者の場合は
            # 実行時間とメモリ消費量を返却しない
            # (NULLの場合はto_dictで設定されないのでpopの引数にNoneを指定)
            t.pop("time", None)
            t.pop("memory", None)
        ret["tests"].append(t)

    return ret
