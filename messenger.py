import databaseConnect
import generateKey
import os
from binascii import hexlify
from flask import make_response, jsonify
import logging


#       Current schema:
#           User:
#               email:
#               id:
#               phone_number:
#               password:
#               salt:
#               api_key:

def createUser(email, password, phoneNumber, name, surname):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    try:
        salt = os.urandom(32)
        key = generateKey.generateKey(password, salt)
        api_key = hexlify(os.urandom(32))
        query = "INSERT INTO messenger_users (email, password, salt, phone_number, api_key, name, surname) " \
                "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (email, key, salt, phoneNumber, api_key, name, surname,))
        connect.commit()
        cursor.close()
        # emailSending.send_email_create_account(email)
        return make_response("User created successfully", 200)
    except Exception:
        cursor.execute("ROLLBACK")
        connect.commit()
        cursor.close()
        return make_response("User already exists", 409)


# Get salt unique for every user
#               Parameters:
# - data: either email or phone number
# - type: can be "email" or "phone number", if not provided "email" will be used
#               Returns:
# - salt: bytes
#
def getSalt(data, type="email"):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    if type == "email":
        query = "SELECT salt FROM messenger_users WHERE email = %s"
    elif type == "phone":
        query = "SELECT salt FROM messenger_users WHERE phone_number = %s"
    cursor.execute(query, (data,))
    connect.commit()
    record = cursor.fetchall()
    cursor.close()
    if len(record) == 0:
        return None
    return record[0][0]


def is_api_key_valid(user_id, api_key):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    query = "SELECT messenger_users.api_key FROM messenger_users WHERE id = %s"
    cursor.execute(query, (user_id,))
    record = cursor.fetchall()
    if len(record) == 0:
        return False
    key_from_db = record[0][0].tobytes().decode("ASCII")
    if key_from_db == api_key:
        return True
    else:
        return False


# User can login using either email or phone number
#               Parameters:
# - password(required):  
# - email(optional):            one of this will be used to 
# - phoneNumber(optional):      get a password from the database
#               Returns:
# - 200: if password is correct
# - 400: if not enough data is provided or password is not correct
#
def loginUser(password, email=None, phoneNumber=None):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    if email is not None:
        salt = getSalt(email)
        query = "SELECT password,id, api_key FROM messenger_users WHERE email = %s"
        cursor.execute(query, (email,))
    elif phoneNumber is not None:
        salt = getSalt(phoneNumber, "phone")
        query = "SELECT password,id, api_key FROM messenger_users WHERE phone_number = %s"
        cursor.execute(query, (phoneNumber,))
    else:
        return make_response("Missing email or phone number", 400)
    if salt is None:
        return make_response("Invalid email or phone number", 400)
    password_provided = generateKey.generateKey(password, salt)
    connect.commit()
    record = cursor.fetchall()
    password_from_db = record[0][0]
    user_id = record[0][1]
    api_key = record[0][2].tobytes().decode("ASCII")
    cursor.close()
    # data coming from database is in form of a memoryview, keep in mind to convert it to bytes with tobytes()
    if password_from_db.tobytes() == password_provided:
        return make_response(jsonify(id=user_id, api_key=api_key), 200)
    else:
        return make_response("Wrong password", 400)


def loadData(userId, apiKey):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        query = "SELECT messenger_users.id, messenger_users.name, messenger_users.surname " \
                "FROM messenger_users, messenger_friends " \
                "WHERE messenger_friends.friend_id = %s " \
                "AND messenger_friends.status = True " \
                "AND messenger_users.id = messenger_friends.user_id"
        cursor.execute(query, (userId,))
        result = cursor.fetchall()
        friends = []
        for friend in result:
            conversation_query = "SELECT " \
                                 "messenger_conversations.last_message, " \
                                 "messenger_conversations.last_message_timestamp " \
                                 "FROM messenger_conversations " \
                                 "WHERE ((user_id = %s AND friend_id = %s) OR " \
                                 "(user_id = %s AND friend_id = %s))"
            cursor.execute(conversation_query, (userId, friend[0], friend[0], userId,))
            record = cursor.fetchall()
            obj = {"id": friend[0],
                   "name": friend[1],
                   "surname": friend[2],
                   "last_message": record[0][0],
                   "last_message_timestamp": record[0][1]}
            friends.append(obj)
        connect.commit()
        cursor.close()
        return make_response(jsonify(friends=friends), 200)
    else:
        cursor.close()
        return make_response("invalid key", 401)


def sendFriendRequest(userId, friendsId, apiKey):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            query = f"INSERT INTO messenger_friends(user_id, friend_id) VALUES ({userId}, {friendsId})"
            cursor.execute(query)
            connect.commit()
            cursor.close()
            return make_response("A request has been send", 200)
        except Exception as error:
            cursor.execute("ROLLBACK")
            connect.commit()
            return make_response("Invalid friend id", 409)
    else:
        cursor.execute("ROLLBACK")
        connect.commit()
        cursor.close()
        return make_response("Invalid user authorization", 401)


def answerFriendRequest(userId, requestId, apiKey, isAccepted):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            if isAccepted:
                # Relationship is stored in two rows, so when the request is accepted we add another row
                query = "UPDATE messenger_friends SET status = True WHERE relation_id = %s"
                cursor.execute(query, (requestId,))
                get_friends_ID = f"SELECT user_id FROM messenger_friends WHERE relation_id = {requestId}"
                cursor.execute(get_friends_ID)
                friends_id = cursor.fetchone()[0]
                insert_relation = "INSERT INTO messenger_friends(user_id, friend_id, status) VALUES (%s, %s, True)"
                cursor.execute(insert_relation, (userId, friends_id,))
                conversation_query = "INSERT INTO messenger_conversations(user_id, friend_id) VALUES (%s, %s)"
                cursor.execute(conversation_query, (userId, friends_id))
            connect.commit()
            cursor.close()
            return make_response("Answer successful", 200)
        except Exception:
            cursor.execute("ROLLBACK")
            connect.commit()
            return make_response("Invalid request id", 409)
    else:
        cursor.close()
        return make_response("Invalid user authorization", 401)


def loadFriendRequests(userId, apiKey):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        query = "SELECT relation_id, user_id FROM messenger_friends WHERE friend_id = %s AND status = False"
        cursor.execute(query, (userId,))
        result = cursor.fetchall()
        requests = []
        for x in result:
            obj = {"relation_id": x[0], "user_id": x[1]}
            requests.append(obj)
        cursor.close()
        return make_response(jsonify(requests=requests), 200)
    else:
        cursor.close()
        return make_response("Invalid user authorization", 401)


def sendMessage(userId, friendsId, message, apiKey):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            query_check_friend = "SELECT * FROM messenger_friends WHERE" \
                                 " user_id = %s AND friend_id = %s" \
                                 " AND status = True"
            cursor.execute(query_check_friend, (userId, friendsId,))
            result = cursor.fetchall()
            if len(result) != 0:
                query_get_conversation_id = "SELECT conversation_id FROM messenger_conversations " \
                                            "WHERE ((user_id = %s AND friend_id = %s) " \
                                            "OR (user_id = %s AND friend_id = %s))"
                cursor.execute(query_get_conversation_id, (userId, friendsId, friendsId, userId,))
                conversation_id = cursor.fetchone()[0]
                query = "INSERT INTO messenger_messages(authors_id, message, conversation_id) " \
                        "VALUES (%s, %s, %s)"
                cursor.execute(query, (userId, message, conversation_id,))
                query_set_conversation_last_message_timestamp = "UPDATE messenger_conversations SET " \
                                                                "last_message_timestamp = current_timestamp, " \
                                                                "last_message = %s " \
                                                                "WHERE conversation_id = %s"
                cursor.execute(query_set_conversation_last_message_timestamp, (message, conversation_id,))
                connect.commit()
                cursor.close()
                return make_response("Message sent successfully", 200)
            cursor.close()
            return make_response("User is not a friend or id is invalid", 406)
        except Exception as e:
            cursor.execute("ROLLBACK")
            connect.commit()
            return make_response("User is not a friend or id is invalid", 406)
    else:
        return make_response("Invalid user authorization", 401)


def loadConversation(userId, apiKey, friendsId):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            query = "SELECT " \
                    "messenger_messages.message_id, " \
                    "messenger_messages.authors_id, " \
                    "messenger_messages.message, " \
                    "messenger_messages.messages_date  " \
                    "FROM messenger_conversations, messenger_messages WHERE" \
                    " ((user_id = %s AND friend_id = %s) " \
                    "OR " \
                    "(user_id = %s AND friend_id = %s)) " \
                    "AND messenger_conversations.conversation_id = messenger_messages.conversation_id " \
                    "ORDER BY  messenger_messages.messages_date DESC"
            cursor.execute(query, (userId, friendsId, friendsId, userId,))
            result = cursor.fetchall()
            conversation = []
            for x in result:
                obj = {"message_id": x[0],
                       "authors_id": x[1],
                       "message": x[2],
                       "message_date": x[3]}
                conversation.append(obj)
            cursor.close()
            return make_response(jsonify(conversation=conversation), 200)
        except Exception as e:
            cursor.execute("ROLLBACK")
            connect.commit()
            return make_response(str(e), 406)
    else:
        return make_response("Invalid user authorization", 401)


def loadUsersByString(userId, apiKey, givenString):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            query = "SELECT messenger_users.id, " \
                    "((messenger_users.name || ' ') || messenger_users.surname) as full_name " \
                    "FROM messenger_users " \
                    "WHERE position(%s in ((messenger_users.name || ' ') || messenger_users.surname))>0 AND " \
                    "messenger_users.id != %s AND " \
                    "messenger_users.id NOT IN " \
                    "(SELECT  messenger_friends.friend_id FROM messenger_friends " \
                    "WHERE messenger_friends.user_id = %s)"
            cursor.execute(query, (givenString, userId, userId,))
            result = cursor.fetchall()
            users = []
            for person in result:
                obj = {"id": person[0], "name": person[1]}
                users.append(obj)
            cursor.close()
            return make_response(jsonify(users=users), 200)
        except Exception as e:
            logging.exception(e)
            return make_response(str(e), 406)
    else:
        cursor.close()
        return make_response("User id or api key is invalid", 401)

# TODO FIX TOO BROAD Exception
