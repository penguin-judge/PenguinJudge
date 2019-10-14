FROM ubuntu
RUN ["apt", "update"]
RUN ["apt", "install", "-y", "g++"]
COPY /compile_scripts /compile_scripts
WORKDIR /compile_scripts
CMD ["sh", "/compile_scripts/compile.sh"]