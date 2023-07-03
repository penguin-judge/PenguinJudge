from datetime import datetime, timedelta
from itertools import groupby
from typing import Any, Dict, List, Optional, Tuple, Union

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException

from penguin_judge import models as m
from penguin_judge.api import schemas
from penguin_judge.api.auth import Claims, require_token_by_config
from penguin_judge.db import Tx, start_transaction

router = APIRouter()


@router.get(
    "", response_model=List[schemas.RankingEntry], response_model_exclude_none=True
)
async def list_rankings(
    contest_id: str,
    claims: Optional[Claims] = Depends(require_token_by_config),
    tx: Tx = Depends(start_transaction),
) -> Any:
    contest = await tx.session.scalar(
        sa.select(m.Contest).where(m.Contest.id == contest_id)
    )
    if not contest:
        raise HTTPException(status_code=404)
    if not contest.is_begun():
        raise HTTPException(status_code=403)

    contest_penalty = contest.penalty
    contest_start_time = contest.start_time
    problems = {
        p.id: p.score
        async for p in await tx.session.stream(
            sa.select(m.Problem.id, m.Problem.score).where(
                m.Problem.contest_id == contest_id
            )
        )
    }

    # 一度も提出していない人をランキングに載せるために利用
    # TODO(*): 過去のコンテストに参加した人も表示されるので、何らかの対応が必要
    users_never_submitted = {
        u.id: u.to_summary_dict()
        async for u, in await tx.session.stream(
            sa.select(m.User).where(m.User.admin.is_(False))
        )
    }

    q = sa.select(
        m.Submission.user_id,
        m.Submission.problem_id,
        m.Submission.status,
        m.Submission.created,
    ).where(
        sa.and_(
            m.Submission.contest_id == contest_id,
            m.Submission.created >= contest.start_time,
            m.Submission.created < contest.end_time,
        )
    )

    users: Dict[int, List[Tuple[str, datetime, m.JudgeStatus]]] = {}
    async for (uid, pid, st, t) in await tx.session.stream(q):
        if uid not in users:
            users[uid] = []
            users_never_submitted.pop(uid, None)
        users[uid].append((pid, t, st))

    user_names = {}
    async for id, name in await tx.session.stream(sa.select(m.User.id, m.User.name)):
        user_names[id] = name

    results = []
    for uid, all_submission in users.items():
        all_submission.sort(key=lambda x: (x[0], x[1]))
        max_time = contest_start_time
        total_score = 0
        total_penalties = 0
        ret = dict(user_id=uid, user_name=user_names[uid], problems={})
        for problem_id, submissions in groupby(all_submission, key=lambda x: x[0]):
            n_penalties = 0
            tmp: Dict[str, Union[float, int, timedelta, bool]] = {}
            has_pending = False
            for _, submit_time, submit_status in submissions:
                if submit_status == m.JudgeStatus.Accepted:
                    tmp["time"] = (submit_time - contest_start_time).total_seconds()
                    score = tmp["score"] = problems[problem_id]
                    max_time = max(max_time, submit_time)
                    total_score += score
                    total_penalties += n_penalties
                    break
                elif submit_status in (m.JudgeStatus.Waiting, m.JudgeStatus.Running):
                    has_pending = True
                elif submit_status not in (
                    m.JudgeStatus.CompilationError,
                    m.JudgeStatus.InternalError,
                ):
                    n_penalties += 1
            tmp["penalties"] = n_penalties
            tmp["pending"] = has_pending
            ret["problems"][problem_id] = tmp
        total_time = max_time - contest_start_time
        ret.update(
            dict(
                time=total_time.total_seconds(),
                score=total_score,
                penalties=total_penalties,
                adjusted_time=(
                    total_time + total_penalties * contest_penalty
                ).total_seconds(),
            )
        )
        results.append(ret)

    results.sort(key=lambda x: (-x["score"], x["adjusted_time"]))
    ranking = 0
    for i, r in enumerate(results):
        if i == 0 or results[i - 1]["score"] != 0:  # 0点の人は同じ順位とする
            ranking += 1
        r["ranking"] = ranking

    # 一度も提出していない人をランキング末尾に同じ順位で追加
    ranking += 1
    for u in users_never_submitted.values():
        results.append(dict(ranking=ranking, user_id=u["id"], problems={}))

    return results
