import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta
import multiprocessing as mp
from functools import partial
from typing import Any, Optional
import pickle
from random import shuffle, uniform
from socket import gethostname
import os

import pika  # type: ignore
from pika.channel import Channel  # type: ignore
from pika.exceptions import AMQPError  # type: ignore
from pika.adapters.asyncio_connection import AsyncioConnection  # type: ignore
from sqlalchemy import func

from penguin_judge.models import (
    Environment, Problem, Submission, JudgeStatus, JudgeResult, TestCase,
    Worker as WorkerTable, transaction)
from penguin_judge.mq import get_mq_conn_params
from penguin_judge.run_container import run


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
        self._conn = AsyncioConnection(
            parameters=get_mq_conn_params(),
            on_open_callback=self._conn_on_open,
            on_open_error_callback=self._conn_on_open_error,
            on_close_callback=self._conn_on_close)
        asyncio.get_event_loop().call_soon_threadsafe(self._update_status)
        asyncio.get_event_loop().run_forever()

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
        pass  # TODO

    def _conn_on_close(self, _: AsyncioConnection, reason: AMQPError) -> None:
        pass  # TODO

    def _ch_on_open(self, ch: Channel) -> None:
        self._ch = ch
        ch.add_on_close_callback(self._ch_on_close)
        ch.queue_declare(
            queue=self._queue_name, callback=self._on_queue_declared)

    def _ch_on_close(self, ch: Channel, reason: AMQPError) -> None:
        # TODO
        try:
            self._conn.close()
        except Exception:
            pass

    def _on_queue_declared(self, method: pika.frame.Method) -> None:
        self._ch.basic_qos(
            prefetch_count=self._max_processes, callback=self._on_basic_qos_ok)

    def _on_basic_qos_ok(self, method: pika.frame.Method) -> None:
        self._start_consuming()

    def _start_consuming(self) -> None:
        self._ch.basic_consume(
            self._queue_name, on_message_callback=self._recv_message)

    def _recv_message(
            self,
            ch: Channel,
            method: pika.spec.Basic.Return,
            properties: pika.spec.BasicProperties,
            body: bytes) -> None:
        def _done(fut: Any) -> None:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self._task_processed += 1
            if fut.exception() is not None:
                self._task_errors += 1
            elif fut.result() == JudgeStatus.InternalError:
                self._task_errors += 1

        try:
            contest_id, problem_id, submission_id = pickle.loads(body)
        except Exception:
            # invalid message. ignore.
            _done(None)
            return

        with transaction() as s:
            submission = s.query(Submission).with_for_update().filter(
                Submission.contest_id == contest_id,
                Submission.problem_id == problem_id,
                Submission.id == submission_id).first()
            if not submission or submission.status != JudgeStatus.Waiting:
                _done(None)
                return
            env = s.query(Environment).filter(
                Environment.id == submission.environment_id).first()
            problem = s.query(Problem).filter(
                Problem.contest_id == contest_id,
                Problem.id == problem_id).first()
            if not env or not problem:
                print('invalid submission (fk error). ignore')
                _done(None)  # TODO(kazuki): 外部キー制約を付与してこのチェックを削除する
                return
            task = submission.to_dict()
            task['environment'] = env.to_dict()
            task['problem'] = problem.to_dict()
            task['tests'] = []
            submission.status = JudgeStatus.Running
            testcases = s.query(TestCase).filter(
                TestCase.contest_id == contest_id,
                TestCase.problem_id == problem_id).all()
            for test in testcases:
                s.add(JudgeResult(
                    contest_id=contest_id,
                    problem_id=problem_id,
                    submission_id=submission_id,
                    test_id=test.id))
                task['tests'].append(test.to_dict())

        # テストの実行順序をシャッフルする
        shuffle(task['tests'])

        def _submit() -> None:
            print('submit to child process', flush=True)
            future = self._executor.submit(run, task)
            future.add_done_callback(_done)
        asyncio.get_event_loop().call_soon_threadsafe(_submit)


def _initializer(db_config: dict) -> None:
    from penguin_judge.models import configure
    print('[worker:child] init {}'.format(db_config), flush=True)
    configure(**db_config)


def main(db_config: dict, max_processes: int) -> None:
    with Worker(db_config, max_processes) as worker:
        worker.start()
