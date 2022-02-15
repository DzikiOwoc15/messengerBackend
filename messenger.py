import psycopg2
import databaseConnect
import generateKey
import emailSending
import os
from binascii import hexlify
from flask import make_response, jsonify


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
    # First check to see if the user already exists
    query = "SELECT * FROM messenger_users WHERE email = %s or phone_number = %s"
    cursor.execute(query, (email, phoneNumber,))
    record = cursor.fetchall()
    connect.close()
    cursor.close()
    if len(record) == 0:
        # This email is not registered yet
        connect2 = databaseConnect.get_connection()
        newCursor = connect2.cursor()
        salt = os.urandom(32)
        print(salt)
        key = generateKey.generateKey(password, salt)
        api_key = hexlify(os.urandom(32))
        query = "INSERT INTO messenger_users (email, password, salt, phone_number, api_key, name, surname) " \
                "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        newCursor.execute(query, (email, key, salt, phoneNumber, api_key, name, surname,))
        connect2.commit()
        connect2.close()
        newCursor.close()
        # emailSending.send_email_create_account(email)
        return make_response("User created successfully", 200)
    else:
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
    connect.close()
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
    connect.close()
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
            obj = {"id": friend[0], "name": friend[1], "surname": friend[2]}
            friends.append(obj)
        connect.commit()
        connect.close()
        cursor.close()
        return make_response(jsonify(friends=friends), 200)
    else:
        connect.close()
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
            connect.close()
            cursor.close()
            return make_response("A request has been send", 200)
        except Exception as error:
            return make_response("Invalid friend id", 409)
    else:
        connect.close()
        cursor.close()
        return make_response("Invalid user authorization", 401)


def answerFriendRequest(userId, requestId, apiKey, isAccepted):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            if isAccepted:
                query = "UPDATE messenger_friends SET status = True WHERE relation_id = %s"
                cursor.execute(query, (requestId,))
                get_friends_ID = f"SELECT user_id FROM messenger_friends WHERE relation_id = {requestId}"
                cursor.execute(get_friends_ID)
                friends_id = cursor.fetchone()[0]
                insert_relation = "INSERT INTO messenger_friends(user_id, friend_id, status) VALUES (%s, %s, True)"
                cursor.execute(insert_relation, (userId, friends_id,))
            connect.commit()
            connect.close()
            cursor.close()
            return make_response("Answer successful", 200)
        except Exception:
            return make_response("Invalid request id", 409)
    else:
        connect.close()
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
        connect.close()
        cursor.close()
        return make_response(jsonify(requests=requests), 200)
    else:
        connect.close()
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
                query = "INSERT INTO messenger_messages(authors_id, receivers_id, message) VALUES (%s, %s, %s)"
                cursor.execute(query, (userId, friendsId, message,))
                connect.commit()
                connect.close()
                cursor.close()
                return make_response("Message sent successfully", 200)
            connect.close()
            cursor.close()
            return make_response("User is not a friend or id is invalid", 406)
        except Exception:
            return make_response("User is not a friend or id is invalid", 406)
    else:
        return make_response("Invalid user authorization", 401)


def loadConversation(userId, apiKey, friendsId):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            query = "SELECT * FROM messenger_messages WHERE" \
                    " ((authors_id = %s AND receivers_id = %s) " \
                    "OR " \
                    "(authors_id = %s AND receivers_id = %s)) " \
                    "ORDER BY  messages_date DESC"
            cursor.execute(query, (userId, friendsId, friendsId, userId,))
            result = cursor.fetchall()
            conversation = []
            for x in result:
                obj = {"message_id": x[0],
                       "authors_id": x[1],
                       "receivers_id": x[2],
                       "message": x[3],
                       "message_date": x[4]}
                conversation.append(obj)
            connect.close()
            cursor.close()
            return make_response(jsonify(conversation=conversation), 200)
        except Exception:
            return make_response("Id invalid", 406)
    else:
        return make_response("Invalid user authorization", 401)


# TODO FIX TOO BROAD Exception