FROM pgvector/pgvector:pg16

# Init script akan dijalankan otomatis saat container pertama kali start
COPY init.sql /docker-entrypoint-initdb.d/init.sql
