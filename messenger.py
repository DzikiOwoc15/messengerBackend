import databaseConnect
import generateKey
import os
from binascii import hexlify
from flask import make_response, jsonify
import logging
import urllib.parse
import logging
import config

logger = logging.getLogger('ftpuploader')


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


def is_user_a_part_of_the_conversation(userId, conversationId, cursor):
    query_check_if_person_is_part_of_the_conversation = "SELECT EXISTS " \
                                                        "(SELECT entry_id " \
                                                        "FROM conversation_users " \
                                                        "WHERE conversation_id = %s AND user_id = %s)"
    cursor.execute(query_check_if_person_is_part_of_the_conversation, (conversationId, userId,))
    return cursor.fetchone()[0]


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
        conversation_users_query = "SELECT " \
                                   "messenger_users.id, " \
                                   "messenger_users.name, " \
                                   "messenger_users.surname, " \
                                   "messenger_conversations.conversation_id, " \
                                   "messenger_conversations.last_message_timestamp, " \
                                   "messenger_conversations.last_message " \
                                   "FROM messenger_users, messenger_conversations, conversation_users " \
                                   "WHERE " \
                                   "messenger_conversations.conversation_id = conversation_users.conversation_id " \
                                   "AND " \
                                   "messenger_users.id = conversation_users.user_id " \
                                   "AND " \
                                   "conversation_users.conversation_id IN " \
                                   "(SELECT conversation_id FROM conversation_users WHERE user_id = %s) "
        cursor.execute(conversation_users_query, (userId,))
        res = cursor.fetchall()
        conversations = []
        for entry in res:
            user_dict = {"name": entry[1],
                         "surname": entry[2],
                         "id": entry[0]}
            conversation_id = entry[3]
            id_found = False
            for x in conversations:
                if x["id"] == conversation_id:
                    id_found = True
                    x["users"].append(user_dict)
            if not id_found:
                last_message_timestamp = entry[4]
                last_message = entry[5]
                entry_dict = {"id": conversation_id,
                              "last_message": last_message,
                              "last_message_timestamp": last_message_timestamp,
                              "users": [user_dict]}
                conversations.append(entry_dict)
        connect.commit()
        cursor.close()
        return make_response(jsonify(conversations=conversations), 200)
    else:
        cursor.close()
        return make_response("invalid key", 401)


def sendFriendRequest(userId, friendsId, apiKey):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            query = f"INSERT INTO messenger_friends(user_id, friend_id) VALUES (%s, %s)"
            cursor.execute(query, (userId, friendsId,))
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
                get_friends_ID = f"SELECT user_id FROM messenger_friends WHERE relation_id = %s"
                cursor.execute(get_friends_ID, (requestId,))
                friends_id = cursor.fetchone()[0]
                insert_relation = "INSERT INTO messenger_friends(user_id, friend_id, status) VALUES (%s, %s, True)"
                cursor.execute(insert_relation, (userId, friends_id,))
                # Create empty conversation row
                conversation_query = "INSERT INTO messenger_conversations DEFAULT VALUES RETURNING conversation_id"
                cursor.execute(conversation_query)
                # Receive it's id
                get_empty_conversation_id = cursor.fetchone()[0]
                # Populate conversation_users with data
                query_insert_user = "INSERT INTO conversation_users(user_id, conversation_id) VALUES (%s, %s)"
                cursor.execute(query_insert_user, (userId, get_empty_conversation_id,))
                cursor.execute(query_insert_user, (friends_id, get_empty_conversation_id,))
            else:
                delete_row_query = "DELETE FROM messenger_friends WHERE relation_id = %s"
                cursor.execute(delete_row_query, (requestId,))
            connect.commit()
            cursor.close()
            return make_response("Answer successful", 200)
        except Exception as E:
            cursor.execute("ROLLBACK")
            connect.commit()
            logger.error(E)
            return make_response(E, 409)
    else:
        cursor.close()
        return make_response("Invalid user authorization", 401)


def loadFriendRequests(userId, apiKey):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        query = "SELECT messenger_friends.relation_id, " \
                "messenger_friends.user_id, " \
                "((messenger_users.name || ' ') || messenger_users.surname) as full_name " \
                "FROM messenger_friends, messenger_users WHERE " \
                "friend_id = %s AND " \
                "status = False AND " \
                "messenger_friends.user_id = messenger_users.id"
        cursor.execute(query, (userId,))
        result = cursor.fetchall()
        requests = []
        for x in result:
            obj = {"relation_id": x[0], "user_id": x[1], "name": x[2]}
            requests.append(obj)
        cursor.close()
        return make_response(jsonify(requests=requests), 200)
    else:
        cursor.close()
        return make_response("Invalid user authorization", 401)


def loadNumberOfFriendRequests(userId, apiKey):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            query = "SELECT COUNT(relation_id) FROM messenger_friends WHERE friend_id = %s and status = False"
            cursor.execute(query, (userId,))
            result = cursor.fetchall()
            return make_response(jsonify(result=result[0]), 200)
        except Exception:
            return make_response("Invalid user id", 401)
    else:
        cursor.close()
        return make_response("Invalid user authorization", 401)


def sendMessage(userId, conversationId, message, apiKey):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            is_part = is_user_a_part_of_the_conversation(userId, conversationId, cursor)
            if is_part:
                query_insert_message = "INSERT INTO messenger_messages (conversation_id, authors_id, message) " \
                                       "VALUES (%s, %s, %s)"
                cursor.execute(query_insert_message, (conversationId, userId, message,))
                connect.commit()
                cursor.close()
                return make_response("Message sent successfully", 200)
            cursor.close()
            logger.error(conversationId)
            return make_response("User is not a friend or id is invalid", 406)
        except Exception as e:
            cursor.execute("ROLLBACK")
            connect.commit()
            logger.error(e)
            return make_response("User is not a friend or id is invalid", 406)
    else:
        return make_response("Invalid user authorization", 401)


def loadConversation(userId, apiKey, conversationId):
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
                    "FROM messenger_messages WHERE " \
                    "messenger_messages.conversation_id = %s " \
                    "ORDER BY  messenger_messages.messages_date ASC"
            cursor.execute(query, (conversationId,))
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


def loadConversationLastMessageTimeStamp(userId, apiKey, conversationId):
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    key_valid = is_api_key_valid(userId, apiKey)
    if key_valid:
        try:
            if is_user_a_part_of_the_conversation(userId, conversationId, cursor):
                query = "SELECT messenger_conversations.last_message_timestamp " \
                        "FROM messenger_conversations " \
                        "WHERE conversation_id = %s "
                cursor.execute(query, (conversationId,))
                result = cursor.fetchone()[0]
                cursor.close()
                return make_response(jsonify(result), 200)
            else:
                cursor.close()
                return make_response("User is not a part of the conversation", 409)
        except Exception:
            cursor.close()
            return make_response("Error", 406)
    else:
        cursor.close()
        return make_response("Invalid userId or ApiKey", 406)


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
            cursor.execute(query, (urllib.parse.unquote(givenString), userId, userId,))
            result = cursor.fetchall()
            users = []
            for person in result:
                obj = {"id": person[0], "name": person[1]}
                users.append(obj)
            cursor.close()
            return make_response(jsonify(users=users), 200)
        except Exception as e:
            logging.exception(e)
            cursor.close()
            return make_response(str(e), 406)
    else:
        cursor.close()
        return make_response("User id or api key is invalid", 401)


def uploadProfilePic(userId, apiKey, picture):
    is_key_valid = is_api_key_valid(userId, apiKey)
    if is_key_valid or userId == 1:
        print(picture.mimetype)
        if picture.mimetype.startswith("image"):
            print("It's a picture!")
            picture.save(f"{config.PROFILE_PICTURE_PATH}\\{userId}.png")
            return make_response("Done", 200)
        else:
            return make_response("File is not an image", 409)
    else:
        return make_response("Invalid user or apiKey", 401)

# TODO FIX TOO BROAD Exception
