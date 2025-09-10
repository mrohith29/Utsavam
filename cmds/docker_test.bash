docker exec -it utsavam-redis redis-cli
- KEYS "event:*:tokens"
- GET "event:4:tokens"

docker exec -it utsavam-postgres psql -U utsavam -d utsavam_dev
- SELECT * FROM events;
- SELECT * FROM bookings;

docker exec -it utsavam-redis redis-cli SET "event:1:tokens" 5
- GET "event:1:tokens"

docker exec -it utsavam-redis redis-cli DEL "event:1:tokens"
- GET "event:1:tokens"