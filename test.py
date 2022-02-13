import connexion
import pytest
import json
import databaseConnect

test_id = None
friend_id = None
api_key = None
friend_api_key = None

test_name = "Kamil"
test_surname = "R"
test_email = "example@com.pl"
wrong_email = "null@null.com"
test_password = "password"
wrong_password = "word"
test_phone = 999666333
wrong_phone = 555444333

friends_name = "Friend"
friends_surname = "Surname"
friends_email = "imafriend@com.pl"
friends_password = "imapassword"
friends_phone = 999888777


@pytest.fixture
def app():
    app = connexion.App(__name__, specification_dir='.')
    app.add_api('messengerSwagger.yml')
    return app.app.test_client()


def test_api(app):
    request = app.get(f"api/my")
    assert request.status_code == 404


def test_user_create(app):
    # Create main account
    response = app.put(
        f"api/createUser?"
        f"email={test_email}&&"
        f"phoneNumber={test_phone}&&"
        f"password={test_password}&&"
        f"name={test_name}&&"
        f"surname={test_surname}")
    assert response.status_code == 200

    # Create friend's account
    response_2 = app.put(
        f"api/createUser?"
        f"email={friends_email}&&"
        f"phoneNumber={friends_phone}&&"
        f"password={friends_password}&&"
        f"name={friends_name}&&"
        f"surname={friends_surname}"
    )
    assert response_2.status_code == 200


def test_user_already_exists_same_email(app):
    second_response = app.put(f"api/createUser?"
                              f"email={test_email}&&"
                              f"phoneNumber={wrong_phone}&&"
                              f"password={test_password}&&"
                              f"name={test_name}&&"
                              f"surname={test_surname}")
    assert second_response.status_code == 409
    assert second_response.get_data(as_text=True) == "User already exists"


def test_user_already_exists_same_phone(app):
    second_response = app.put(f"api/createUser?"
                              f"email={wrong_email}&&"
                              f"phoneNumber={test_phone}&&"
                              f"password={test_password}&&"
                              f"name={test_name}&&"
                              f"surname={test_surname}")
    assert second_response.status_code == 409
    assert second_response.get_data(as_text=True) == "User already exists"


def test_login_user_using_email(app):
    successful_login = app.get(f"api/loginUser?email={test_email}&&password={test_password}")
    assert successful_login.status_code == 200
    assert "api_key" in successful_login.get_data(as_text=True)
    assert "id" in successful_login.get_data(as_text=True)


def test_login_user_using_phone(app):
    global test_id, api_key, friend_id, friend_api_key
    successful_login = app.get(f"api/loginUser?phoneNumber={test_phone}&&password={test_password}")
    assert successful_login.status_code == 200
    assert "api_key" in successful_login.get_data(as_text=True)
    assert "id" in successful_login.get_data(as_text=True)

    data = json.loads(successful_login.get_data(as_text=True))
    test_id = data["id"]
    api_key = data["api_key"]

    friends_login = app.get(f"api/loginUser?phoneNumber={friends_phone}&&password={friends_password}")
    assert friends_login.status_code == 200
    friends_data = json.loads(friends_login.get_data(as_text=True))
    friend_id = friends_data["id"]
    friend_api_key = friends_data["api_key"]


def test_login_user_wrong_email(app):
    failed_login = app.get(f"api/loginUser?email={wrong_email}&&password={wrong_password}")
    assert failed_login.status_code == 400
    assert failed_login.get_data(as_text=True) == "Invalid email or phone number"


def test_login_user_wrong_phone(app):
    failed_login = app.get(f"api/loginUser?phoneNumber={wrong_phone}&&password={wrong_password}")
    assert failed_login.status_code == 400
    assert failed_login.get_data(as_text=True) == "Invalid email or phone number"


def test_add_friend(app):
    request = app.put(f"api/sendFriendRequest?userId={test_id}&&friendsId={friend_id}&&apiKey={api_key}")
    assert request.status_code == 200

    # Check the database for the request
    connect = databaseConnect.get_connection()
    cursor = connect.cursor()
    query = f"SELECT * FROM messenger_friends WHERE user_id = {test_id}"
    cursor.execute(query)
    record = cursor.fetchall()
    assert record[0][2] == friend_id
    assert record[0][1] == test_id
    assert not record[0][3]


# Confirm the request
def test_confirm_friend_request(app):
    request = app.put(f"api/answerFriendRequest?"
                      f"userId={friend_id}&&"
                      f"requestId={test_id}&&"
                      f"apiKey={friend_api_key}&&"
                      f"decision={True}")
    assert request.status_code == 200


def test_add_friend_invalid_friends_id(app):
    request = app.put(f"api/sendFriendRequest?userId={test_id}&&friendsId={0}&&apiKey={api_key}")
    assert request.status_code == 409


def test_add_friend_invalid_api_key(app):
    invalid_key = "none"
    request = app.put(f"api/sendFriendRequest?userId={test_id}&&friendsId={0}&&apiKey={invalid_key}")
    assert request.status_code == 401


def test_login_user_wrong_password(app):
    failed_login = app.get(f"api/loginUser?email={test_email}&&password={wrong_password}")
    assert failed_login.status_code == 400
    assert failed_login.get_data(as_text=True) == "Wrong password"


def test_delete_user(app):
    # Delete user and friend instance after the test
    connection = databaseConnect.get_connection()
    cursor = connection.cursor()
    query_friends = f"DELETE FROM messenger_friends WHERE user_id = {test_id}"
    cursor.execute(query_friends)
    query = "DELETE FROM messenger_users WHERE email = %s or email = %s"
    cursor.execute(query, (test_email, friends_email,))
    connection.commit()
    connection.close()
    cursor.close()


