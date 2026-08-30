import os
import pymysql
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PORT = int(os.getenv("DB_PORT", "0") or 0)
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "defaultdb").strip()
DB_SSL_CA = os.getenv("DB_SSL_CA", "").strip()

def get_db_conn():
    missing = []
    if not DB_HOST:
        missing.append("DB_HOST")
    if not DB_PORT:
        missing.append("DB_PORT")
    if not DB_USER:
        missing.append("DB_USER")
    if not DB_PASSWORD:
        missing.append("DB_PASSWORD")
    if missing:
        raise RuntimeError("필수 DB 환경변수가 없습니다: " + ", ".join(missing))

    options = dict(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        autocommit=False,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
    )
    if DB_SSL_CA:
        options["ssl"] = {"ca": DB_SSL_CA}
    else:
        options.update(
            ssl_verify_cert=False,
            ssl_verify_identity=False,
        )

    return pymysql.connect(**options)
