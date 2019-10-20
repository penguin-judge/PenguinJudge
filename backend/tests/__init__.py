import os


def _db_url():
    if 'PENGUIN_JUDGE_TEST_DB_URL' in os.environ:
        return os.environ['PENGUIN_JUDGE_TEST_DB_URL']
    return 'postgresql://penguin:penguin@localhost:5432/penguin_judge_test'


TEST_DB_URL = _db_url()
