import requests
import pytest
from common.request_util import RequestUtil
from api.user_api import login_api, update_nickname_api


@pytest.mark.parametrize("username, password ,expected_status, expected_code",[
    ("test","123456",200,0),
    ("test","wrong_password",200,1001),])
def test_login_parametrize(username,password,expected_status,expected_code):
    res = login_api(username,password)
    data = res.json()
    assert res.status_code == expected_status
    assert data["code"] == expected_code



@pytest.mark.parametrize("nickname, expected_status, expected_code", [
    ("valid_name", 200, 0),
    ("", 200, 2001),
])
def test_update_nickname(login,nickname, expected_status, expected_code):
    res = update_nickname_api(login, nickname)
    data = res.json()
    assert data["code"] == expected_code
    assert res.status_code == expected_status