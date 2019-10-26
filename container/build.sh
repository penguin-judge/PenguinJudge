#!/bin/bash
set -eu

# build agent
(cd ../agent && ./build_static_binary.sh)
AGENT_NAME=penguin_judge_agent
AGENT_PATH=../agent/target/x86_64-unknown-linux-musl/release/${AGENT_NAME}

# build all
for dockerfile in $(find . -type f -and -name "Dockerfile*"); do
    env_name=${dockerfile%/*}
    env_name=${env_name##*/}
    image_name="penguin_judge_${env_name}"
    filename=${dockerfile##*/}
    tag=${dockerfile##*:}
    tmp=${filename%:*}
    sub_name=${tmp##*.}
    if [ "$tmp" = "$sub_name" ]; then
        image_name=${image_name}:$tag
    else
        image_name=${image_name}_${sub_name}:$tag
    fi
    cp -a "$AGENT_PATH" "${env_name}/"
    (cd "$env_name"; docker build -f $filename -t ${image_name} . ; rm "$AGENT_NAME")
done
