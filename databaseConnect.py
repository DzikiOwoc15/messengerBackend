import psycopg2
import config

current_connection = None


def get_connection():
    global current_connection
    if current_connection is None or current_connection.closed != 0:
        current_connection = psycopg2.connect(user=config.DB_USER, password=config.DB_PASSWORD, database=config.DB)
    return current_connection

