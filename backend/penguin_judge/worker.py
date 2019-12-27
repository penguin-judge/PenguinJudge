import asyncio
from concurrent.futures import ProcessPoolExecutor, Future
from datetime import timedelta
import multiprocessing as mp
from functools import partial
from typing import Any, Optional
import pickle
from random import shuffle, uniform
from socket import gethostname
import os
from logging import getLogger

import pika  # type: ignore
from pika.channel import Channel  # type: ignore
from pika.exceptions import AMQPError  # type: ignore
from pika.adapters.asyncio_connection import AsyncioConnection  # type: ignore
from sqlalchemy import func

from penguin_judge.models import (
    Environment, Problem, Submission, JudgeStatus, JudgeResult, TestCase,
    Worker as WorkerTable, transaction)
from penguin_judge.mq import get_mq_conn_params
from penguin_judge.judge.docker import DockerJudgeDriver
from penguin_judge.judge.main import run

LOGGER = getLogger(__name__)


class Worker(object):
    def __init__(self, db_config: dict, max_processes: int) -> None:
        self._max_processes = max_processes
        self._executor = ProcessPoolExecutor(
            max_workers=max_processes,
            mp_context=mp.get_context('spawn'),
            initializer=partial(_initializer, db_config))
        self._queue_name = 'judge_queue'
        self._conn: AsyncioConnection = None
        self._ch: Channel = None
        self._hostname: Optional[str] = None
        self._pid = os.getpid()
        self._task_processed, self._task_errors = 0, 0
        self._maint_interval = timedelta(seconds=60)

    def __enter__(self) -> 'Worker':
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self._executor.shutdown(wait=False)
        if self._ch:
            self._ch.close()
        if self._conn:
            self._conn.close()

    def start(self) -> None:
        self._connect()
        asyncio.get_event_loop().call_soon_threadsafe(self._update_status)
        asyncio.get_event_loop().run_forever()

    def _connect(self) -> None:
        self._conn = AsyncioConnection(
            parameters=get_mq_conn_params(),
            on_open_callback=self._conn_on_open,
            on_open_error_callback=self._conn_on_open_error,
            on_close_callback=self._conn_on_close)

    def _schedule_update_status(self) -> None:
        asyncio.get_event_loop().call_later(
            uniform(
                self._maint_interval.total_seconds() - 1,
                self._maint_interval.total_seconds() + 1,
            ), self._update_status)

    def _update_status(self) -> None:
        updates = dict(
            last_contact=func.now(),
            processed=self._task_processed,
            errors=self._task_errors,
        )
        try:
            hostname = self._hostname or gethostname()
            with transaction() as s:
                if self._hostname:
                    s.query(WorkerTable).filter(
                        WorkerTable.hostname == self._hostname,
                        WorkerTable.pid == self._pid
                    ).update(updates, synchronize_session=False)
                else:
                    updates.update(dict(
                        hostname=hostname, pid=self._pid,
                        max_processes=self._max_processes,
                        startup_time=func.now()))
                    s.add(WorkerTable(**updates))
                if uniform(0, 1) <= 0.01 or not self._hostname:
                    threshold = self._maint_interval * 10
                    s.query(WorkerTable).filter(
                        func.now() - WorkerTable.last_contact > threshold
                    ).delete(synchronize_session=False)
            self._hostname = hostname
        except Exception:
            pass
        self._schedule_update_status()

    def _conn_on_open(self, _: AsyncioConnection) -> None:
        self._conn.channel(on_open_callback=self._ch_on_open)

    def _conn_on_open_error(self, _: AsyncioConnection,
                            err: AMQPError) -> None:
        LOGGER.warning(
            'Cannot open RabbitMQ connection({}). retrying...'.format(err))
        asyncio.get_event_loop().call_later(uniform(1, 5), self._connect)

    def _conn_on_close(self, _: AsyncioConnection, reason: AMQPError) -> None:
        LOGGER.warning(
            'RabbitMQ connection closed({}). retrying...'.format(reason))
        asyncio.get_event_loop().call_later(uniform(1, 5), self._connect)

    def _ch_on_open(self, ch: Channel) -> None:
        self._ch = ch
        ch.add_on_close_callback(self._ch_on_close)
        ch.queue_declare(
            queue=self._queue_name, callback=self._on_queue_declared)

    def _ch_on_close(self, ch: Channel, reason: AMQPError) -> None:
        LOGGER.warning('RabbitMQ channel closed ({})'.format(reason))
        try:
            self._conn.close()
        except Exception:
            pass

    def _on_queue_declared(self, method: pika.frame.Method) -> None:
        self._ch.basic_qos(
            prefetch_count=self._max_processes, callback=self._on_basic_qos_ok)

    def _on_basic_qos_ok(self, method: pika.frame.Method) -> None:
        self._ch.basic_consume(
            self._queue_name, on_message_callback=self._recv_message)
        LOGGER.info('Worker started')

    def _recv_message(
            self,
            ch: Channel,
            method: pika.spec.Basic.Return,
            _: pika.spec.BasicProperties,
            body: bytes) -> None:
        try:
            self._process(ch, method, body)
        except Exception:
            LOGGER.warning('', exc_info=True)

    def _process(
            self,
            ch: Channel,
            method: pika.spec.Basic.Return,
            body: bytes) -> None:
        def _done(fut: Optional[Future]) -> None:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            if fut is None:
                return
            self._task_processed += 1
            if fut.exception() is not None:
                self._task_errors += 1
            elif fut.result() == JudgeStatus.InternalError:
                self._task_errors += 1

        try:
            contest_id, problem_id, submission_id = pickle.loads(body)
        except Exception:
            LOGGER.warning('Received invalid message. ignored.', exc_info=True)
            _done(None)
            return

        with transaction() as s:
            submission = s.query(Submission).with_for_update().filter(
                Submission.contest_id == contest_id,
                Submission.problem_id == problem_id,
                Submission.id == submission_id).first()
            if not submission:
                LOGGER.warning(
                    'Submission.id "{}" is not found'.format(submission_id))
                _done(None)
            if submission.status not in (
                    JudgeStatus.Waiting, JudgeStatus.Running,
                    JudgeStatus.InternalError):
                _done(None)
            env = s.query(Environment).filter(
                Environment.id == submission.environment_id).first()
            problem = s.query(Problem).filter(
                Problem.contest_id == contest_id,
                Problem.id == problem_id).first()
            assert env and problem  # env/problemは外部キー制約によって常に取得可能

            # ワーカーダウン等ですべてのテストのジャッジが完了していない場合は
            # ジャッジ済みのテストは結果を流用する
            existed_results = {
                jr.test_id: jr
                for jr in s.query(JudgeResult).filter(
                        JudgeResult.contest_id == contest_id,
                        JudgeResult.problem_id == problem_id,
                        JudgeResult.submission_id == submission_id)}

            task = submission.to_dict()
            task['environment'] = env.to_dict()
            task['problem'] = problem.to_dict()
            task['tests'] = []
            submission.status = JudgeStatus.Running
            testcases = s.query(TestCase).filter(
                TestCase.contest_id == contest_id,
                TestCase.problem_id == problem_id).all()
            for test in testcases:
                jr = existed_results.get(test.id, None)
                if not jr:
                    s.add(JudgeResult(
                        contest_id=contest_id, problem_id=problem_id,
                        submission_id=submission_id, test_id=test.id))
                if not jr or jr.status in (
                        JudgeStatus.Waiting, JudgeStatus.Running,
                        JudgeStatus.InternalError):
                    task['tests'].append(test.to_dict())

        # テストの実行順序をシャッフルする
        shuffle(task['tests'])

        def _submit() -> None:
            LOGGER.info('submit to child process (submission.id={})'.format(
                submission_id))
            future = self._executor.submit(run, DockerJudgeDriver, task)
            future.add_done_callback(_done)
        asyncio.get_event_loop().call_soon_threadsafe(_submit)


def _initializer(db_config: dict) -> None:
    from penguin_judge.models import configure
    configure(**db_config)


def main(db_config: dict, max_processes: int) -> None:
    with Worker(db_config, max_processes) as worker:
        worker.start()
