# Postgres container for utsavam
docker run -d --name utsavam-postgres `
  -e POSTGRES_USER=utsavam `
  -e POSTGRES_PASSWORD=utsavam_pass `
  -e POSTGRES_DB=utsavam_dev `
  -p 5433:5432 `
  -v utsavam_pgdata:/var/lib/postgresql/data `
  postgres:15


# Redis container for utsavam
docker run -d --name utsavam-redis -p 6379:6379 redis:7

