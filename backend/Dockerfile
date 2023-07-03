FROM python:3.11-slim

COPY pyproject.toml /work/
RUN cd /work \
  && mkdir penguin_judge \
  && touch penguin_judge/__init__.py \
  && pip install . \
  && pip uninstall -y penguin_judge \
  && rm -rf ~/.cache /work /usr/local/lib/*/site-packages/penguin_judge \
  && mkdir /work \
  && useradd -m penguin_judge

COPY pyproject.toml /work/
COPY penguin_judge /work/penguin_judge
RUN cd /work \
  && pip install . \
  && rm -rf ~/.cache /work

USER penguin_judge
