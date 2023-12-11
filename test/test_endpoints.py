import json

import pytest
from api import create_app


@pytest.fixture
def app():
    app = create_app()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# General Endpoints Tests
def test_index(client):
    response = client.get('/')
    assert(response.status_code, 200)


def test_poll(client):
    response = client.get('/poll')
    json_data = json.loads(response.data.decode('utf-8'))

    assert(response.status_code, 200)
    assert(json_data['success'], True)
    assert(json_data['message'], 'Flask and MongoDB are UP!')


def test_resource_not_found(client):
    response = client.get("/resource_not_found")

    assert(response.status_code, 404)


# Auth Endpoints Tests
def test_add_user(client):
    response = client.post(
        "/login/addUser",
        data=json.dumps({"username": "test", "password": "test"}),
        content_type="application/json",
    )
    json_data = json.loads(response.data.decode('utf-8'))

    assert(response.status_code, 200)
    assert(json_data['success'], True)


def test_delete_user(client):
    response = client.post(
        "/login/deleteUser",
        data=json.dumps({"username": "test", "password": "test"}),
        content_type="application/json",
    )
    json_data = json.loads(response.data.decode('utf-8'))

    assert(response.status_code, 200)
    assert(json_data['success'], True)
    assert(json_data['message'], 'User deleted successfully')


if __name__ == '__main__':
    # Run all tests in the module
    pytest.main()
