from typing import TypeVar

from penguin_judge.db.models import (
    User, Contest, Problem, TestCase, Environment,
    configure, transaction)

T = TypeVar('T')


def prepare() -> None:
    configure(drop_all='True')
    with transaction() as s:
        def _add(o: T) -> T:
            s.add(o)
            s.flush()
            return o

        _add(User(
            id='kazuki', name='Kazuki Oikawa', salt=b'foo', password=b'bar'))
        _add(Environment(name='Python 3.7', config={}))
        contest = _add(Contest(
            id='abc000', title='ABC 001', description='description'))
        prob_a = _add(Problem(
            contest_id=contest.id, id='a', title='one plus one',
            description='"いちたすいち"を計算してね'))
        _add(TestCase(
            contest_id=contest.id, problem_id=prob_a.id, id='0', input=b'',
            output=b'2'))
        prob_b = _add(Problem(
            contest_id=contest.id, title='max', id='b',
            description='"X Y"という形式で標準入力から与えられるので大きな方の'
                        '値を力してね'))
        _add(TestCase(
            contest_id=contest.id, problem_id=prob_b.id, id='0',
            input=b'1 123', output=b'123'))
        _add(TestCase(
            contest_id=contest.id, problem_id=prob_b.id, id='1',
            input=b'234 99', output=b'234'))


if __name__ == '__main__':
    prepare()
