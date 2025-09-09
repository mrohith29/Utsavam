import os
import sys
import psycopg2

url = os.getenv("DATABASE_URL", "postgresql://utsavam:utsavam_pass@localhost:5432/utsavam_dev")
print("Testing:", url)
try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print("OK - server version:", cur.fetchone())
    cur.close()
    conn.close()
except Exception as e:
    print("CONNECT ERROR:", repr(e))
    sys.exit(1)
