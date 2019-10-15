curl localhost:5000/user/2917cdeb49f938b
curl -X POST -H 'Content-Type:application/json' -d "{\"name\":\"kazuki\",\"password\":\"1234\"}" localhost:5000/user
curl localhost:5000/contests/1/problems/1/submission
curl localhost:5000/contests/1/problems/1/submission/all