FROM python:3.7-slim

# 依存関係は更新が少ないので別レイヤでインストール
ADD Pipfile Pipfile.lock setup.py /work/
RUN cd /work && pip install . && rm -rf ~/.cache

# 本体をインストール
ADD penguin_judge /work/penguin_judge/
RUN cd /work && pip install .
