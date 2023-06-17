FROM python:3.7-slim

# 依存関係は更新が少ないので別レイヤでインストール
ADD Pipfile Pipfile.lock setup.py /work/
RUN cd /work && pip install . && \
   pip install \
       markupsafe==2.0.1 \
       openapi-spec-validator==0.2.10 \
       urllib3==1.25.9 \
       requests==2.24.0 \
   && rm -rf ~/.cache

# 本体をインストール
ADD penguin_judge /work/penguin_judge/
RUN cd /work && pip install .
