
from common.request_util import RequestUtil
from conftest import login


def login_api(username,password):
    res = RequestUtil("post","url", json={"username": username, "password":password})
    return res


def update_nickname_api(token, nickname):
    res = RequestUtil("post","url", headers={"Authorization": f"Bearer {token}"}, json={"nickname": nickname})       
    return res