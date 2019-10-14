curl localhost:5000/contests
curl localhost:5000/contests/1
#curl -X POST -H 'Content-Type:application/json' -d "{}" localhost:5000/contests/1/problems/1
#curl -X POST -H 'Content-Type:application/json' -d "{\"code\":\"int main(){}\",\"environment_id\":\"1\"}" localhost:5000/contests/1/problems/1
curl -X POST -H 'Content-Type:application/json' -d "{\"code\":\"#include<stdio.h>\n#include<unistd.h>\n int main(){ sleep(10); int a; scanf(\\\"%d\\\", &a); printf(\\\"%d\\\",a);}\",\"environment_id\":\"1\"}" localhost:5000/contests/1/problems/1