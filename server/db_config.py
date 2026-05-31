import pymysql

DB_HOST = "mysql-16c9b96-smishing-94b5.h.aivencloud.com"
DB_PORT = 23429
DB_USER = "avnadmin"
DB_PASSWORD = ""
DB_NAME = "defaultdb"

def get_db_conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        autocommit=False,
        ssl_verify_cert=False,
        ssl_verify_identity=False,
    )
