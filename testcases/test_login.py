import requests
import pytest
from common.request_util import RequestUtil

def test_login_success():
    res = RequestUtil("post","url", json={"username": "test", "password": "1234567"})
    data = res.json()
    assert res.status_code == 200
    assert data["code" ] == 1001



def test_rename_success(login):
    #token = login
    assert login is not None
    res = RequestUtil("post","url", headers={"Authorization": f"Bearer {login}"}, json={"nickname": "new_name"})
    assert res.status_code == 200
    assert res.json()["code"] == 0
def test_rename_fail(login):
#
    assert login is not None
    res = RequestUtil("post","url", headers={"Authorization": f"Bearer {login}"}, json={"nickname": ""})
    assert res.status_code == 200
    assert res.json()["code"] == 2001
