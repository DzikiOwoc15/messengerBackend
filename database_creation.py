import databaseConnect
import psycopg2


# messenger_user:
#   id: integer
#   name: text
#   surname: text
#   email:  text
#   phone_number: text
#   password: bytea
#   salt: bytea
#   api_key: bytea
#
def create_table_users():
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    query = """CREATE TABLE messenger_users(
            id integer NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
            email text NOT NULL,
            name text NOT NULL,
            surname text NOT NULL,
            phone_number text NOT NULL,
            password bytea NOT NULL,
            salt bytea NOT NULL,
            api_key bytea NOT NULL,
            CONSTRAINT messengerusers_pkey PRIMARY KEY (id)
            )
        """
    cursor.execute(query)
    connect.commit()
    cursor.close()
    connect.close()


#   messenger_friends:
#       relation_id: integer
#       user_id: integer
#       friend_id: integer
#       status: boolean
#
def create_table_friends():
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    query = """CREATE TABLE messenger_friends(
              relation_id INTEGER NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
              user_id integer NOT NULL REFERENCES messenger_users (id),
              friend_id INTEGER NOT NULL REFERENCES messenger_users(id),
              status BOOLEAN NOT NULL DEFAULT FALSE
            )
    """
    cursor.execute(query)
    connect.commit()
    cursor.close()
    connect.close()


# messenger_messages
#       message_id: integer
#       authors_id: integer
#       receivers_id: integer
#       message: text
#       messages_date: timestamp
#
def create_table_messages():
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    query = """CREATE TABLE messenger_messages(
                message_id INTEGER NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
                authors_id INTEGER NOT NULL REFERENCES messenger_users (id),
                receivers_id INTEGER NOT NULL REFERENCES messenger_users (id),
                message TEXT NOT NULL,
                messages_date TIMESTAMP NOT NULL DEFAULT current_timestamp
            )
    """
    cursor.execute(query)
    connect.commit()
    cursor.close()
    connect.close()



