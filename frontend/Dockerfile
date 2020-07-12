FROM node:slim AS builder
ADD *.json *.js /work/
RUN cd /work && npm ci

ADD public /work/public/
ADD src /work/src/
RUN cd /work && node_modules/.bin/webpack -p && \
    cp dist/* public/ && \
    cp node_modules/katex/dist/fonts/* public/fonts/

FROM nginx:stable-alpine
COPY --from=builder /work/public /usr/share/nginx/html
COPY nginx.sample.conf /etc/nginx/conf.d/default.conf
