import requests
import pytest
from common.request_util import RequestUtil
from api.user_api import login_api, update_nickname_api

def test_login_success():
    res = login_api("test", "123456")
    data = res.json()
    assert data["code"] == 0
    assert res.status_code == 200
def test_login_fail():
    res = login_api("test", "wrong_password")
    data = res.json()
    assert data["code"] == 1001
    assert res.status_code == 200


def test_rename_success(login):
    #token = login
    assert login is not None
    res = update_nickname_api(login, "new_name")
    data = res.json()
    assert data["code"] == 0
    assert res.status_code == 200

def test_rename_fail(login):
#
    assert login is not None
    res = update_nickname_api(login, "")
    data = res.json()
    assert data["code"] == 2001
    assert res.status_code == 200
    assert res.json()["code"] == 2001
