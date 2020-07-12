#!/bin/sh

docker pull penguinjudge/agent_go_compile:1.13.4
docker tag penguinjudge/agent_go_compile:1.13.4 penguin_judge_go_compile:1.13.4
docker pull penguinjudge/agent_go_judge:1.13.4
docker tag penguinjudge/agent_go_judge:1.13.4 penguin_judge_go_judge:1.13.4
docker pull penguinjudge/agent_python_judge:3.7
docker tag penguinjudge/agent_python_judge:3.7 penguin_judge_python:3.7
docker pull penguinjudge/agent_rust_compile:1.39.0
docker tag penguinjudge/agent_rust_compile:1.39.0 penguin_judge_rust_compile:1.39.0
docker pull penguinjudge/agent_rust_judge:1.39.0
docker tag penguinjudge/agent_rust_judge:1.39.0 penguin_judge_rust_judge:1.39.0
docker pull penguinjudge/agent_java_compile:14
docker tag penguinjudge/agent_java_compile:14 penguin_judge_java_compile:14
docker pull penguinjudge/agent_java_judge:14
docker tag penguinjudge/agent_java_judge:14 penguin_judge_java_judge:14
docker pull penguinjudge/agent_pypy3.6_judge:7.2
docker tag penguinjudge/agent_pypy3.6_judge:7.2 penguin_judge_pypy3.6:7.2.0
docker pull penguinjudge/agent_cpp_compile:8.2
docker tag penguinjudge/agent_cpp_compile:8.2 penguin_judge_cpp_compile:8.2
docker pull penguinjudge/agent_cpp_judge:8.2
docker tag penguinjudge/agent_cpp_judge:8.2 penguin_judge_cpp_judge:8.2
docker pull penguinjudge/agent_node_judge:12.13.0
docker tag penguinjudge/agent_node_judge:12.13.0 penguin_judge_node:12.13.0
docker pull penguinjudge/agent_c_compile:8.2
docker tag penguinjudge/agent_c_compile:8.2 penguin_judge_c_compile:8.2
docker pull penguinjudge/agent_c_judge:8.2
docker tag penguinjudge/agent_c_judge:8.2 penguin_judge_c_judge:8.2
docker pull penguinjudge/agent_ruby_judge:2.6.5
docker tag penguinjudge/agent_ruby_judge:2.6.5 penguin_judge_ruby:2.6.5
