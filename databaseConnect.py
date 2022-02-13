import psycopg2
import config


def get_connection():
    connect = psycopg2.connect(user=config.DB_USER, password=config.DB_PASSWORD, database=config.DB)
    return connect
