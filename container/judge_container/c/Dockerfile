FROM ubuntu
RUN ["apt", "update"]
RUN ["apt", "install", "-y", "g++"]
RUN ["apt", "install", "-y", "time"]
COPY /judge_scripts /judge_scripts
WORKDIR /judge_scripts