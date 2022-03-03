import databaseConnect
import psycopg2


#   messenger_user:
#       id: integer
#       name: text
#       surname: text
#       email:  text
#       phone_number: text
#       password: bytea
#       salt: bytea
#       api_key: bytea
#
def create_table_users():
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    query = """CREATE TABLE messenger_users(
            id integer NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
            email text NOT NULL UNIQUE,
            name text NOT NULL,
            surname text NOT NULL,
            phone_number text NOT NULL UNIQUE,
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


#   messenger_conversations:
#       conversation_id: integer
#       last_message_timestamp: timestamp
#       last_message: text
#
def create_table_conversations():
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    query = """CREATE TABLE messenger_conversations(
                conversation_id INTEGER NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
                last_message_timestamp TIMESTAMP,
                last_message TEXT
            )
    """
    cursor.execute(query)
    connect.commit()
    cursor.close()
    connect.close()


#   conversation_users:
#       entry_id: integer
#       user_id: integer
#       conversation_id: integer
#
def create_table_conversation_users():
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    query = """CREATE TABLE conversation_users(
                    entry_id INTEGER NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
                    user_id INTEGER NOT NULL REFERENCES messenger_users (id),
                    conversation_id INTEGER NOT NULL REFERENCES messenger_conversations (conversation_id)
            )
    """
    cursor.execute(query)
    connect.commit()
    cursor.close()
    connect.close()


#   messenger_messages:
#       message_id: integer
#       conversation_id: integer
#       authors_id: integer
#       message: text
#       messages_date: timestamp
#
def create_table_messages():
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    query = """CREATE TABLE messenger_messages(
                message_id INTEGER NOT NULL PRIMARY KEY GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
                conversation_id INTEGER NOT NULL REFERENCES messenger_conversations(conversation_id),
                authors_id INTEGER NOT NULL REFERENCES messenger_users (id),
                message TEXT NOT NULL,
                messages_date TIMESTAMP NOT NULL DEFAULT current_timestamp
            )
    """
    cursor.execute(query)
    connect.commit()
    cursor.close()
    connect.close()


create_table_users()
create_table_friends()
create_table_conversations()
create_table_conversation_users()
create_table_messages()
