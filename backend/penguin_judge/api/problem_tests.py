import os
from contextlib import ExitStack
from tempfile import TemporaryFile
from typing import Any
from urllib.parse import quote
from zipfile import ZipFile

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.dialects.postgresql import insert as pg_insert
from zstandard import ZstdCompressor, ZstdDecompressor

from penguin_judge import models as m
from penguin_judge.api.auth import Claims, require_admin_token
from penguin_judge.db import Tx, start_transaction

router = APIRouter()


@router.get("", response_model=list[str])
async def list_tests(
    contest_id: str,
    problem_id: str,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    return (
        await tx.session.scalars(
            sa.select(m.TestCase.id).where(
                sa.and_(
                    m.TestCase.contest_id == contest_id,
                    m.TestCase.problem_id == problem_id,
                )
            )
        )
    ).all()


@router.put("")
async def upload_test_dataset(
    contest_id: str,
    problem_id: str,
    req: Request,
    _: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    zctx = ZstdCompressor()
    test_cases = []
    with ExitStack() as stack:
        f = stack.enter_context(TemporaryFile())
        async for chunk in req.stream():
            f.write(chunk)
        f.seek(0)

        z = stack.enter_context(ZipFile(f))
        path_mapping = {
            os.path.splitext(os.path.basename(x))[0]: os.path.splitext(x)[0]
            for x in z.namelist()
            if x.endswith(".in") or x.endswith(".out")
        }
        for test_case_id, zip_path in path_mapping.items():
            try:
                with z.open(f"{zip_path}.in") as zi:
                    in_data = zctx.compress(zi.read())
                with z.open(f"{zip_path}.out") as zo:
                    out_data = zctx.compress(zo.read())
            except Exception:
                continue
            test_cases.append(
                dict(
                    contest_id=contest_id,
                    problem_id=problem_id,
                    id=test_case_id,
                    input=in_data,
                    output=out_data,
                )
            )

    upsert_stmt = pg_insert(m.TestCase).values(test_cases)
    await tx.session.execute(
        upsert_stmt.on_conflict_do_update(
            index_elements=["contest_id", "problem_id", "id"],
            set_=dict(
                input=upsert_stmt.excluded.input, output=upsert_stmt.excluded.output
            ),
        )
    )
    ret = [tc["id"] for tc in test_cases]
    await tx.commit()
    return ret


@router.get("/{test_id}/in")
async def get_test_input_data(
    contest_id: str,
    problem_id: str,
    test_id: str,
    _: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    return await _get_test_data(contest_id, problem_id, test_id, True, tx)


@router.get("/{test_id}/out")
async def get_test_output_data(
    contest_id: str,
    problem_id: str,
    test_id: str,
    _: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    return await _get_test_data(contest_id, problem_id, test_id, False, tx)


async def _get_test_data(
    contest_id: str, problem_id: str, test_id: str, is_input: bool, tx: Tx
) -> Any:
    zctx = ZstdDecompressor()
    tc = await tx.session.scalar(
        sa.select(m.TestCase).where(
            sa.and_(
                m.TestCase.contest_id == contest_id,
                m.TestCase.problem_id == problem_id,
                m.TestCase.id == test_id,
            )
        )
    )
    if not tc:
        raise HTTPException(status_code=404)
    test_data_raw = zctx.decompress(tc.input if is_input else tc.output)
    filename = f'{test_id}.{"in" if is_input else "out"}'
    escaped_filename = quote(filename, safe="", encoding="utf8")
    headers = {
        "Content-Disposition": f"attachment; filename*=utf-8''{escaped_filename}"
    }
    return Response(test_data_raw, headers=headers)
