import pytest
from common.request_util import RequestUtil
@pytest.fixture(scope="module")
def login():
    res = RequestUtil("post","url", json={"username": "test", "password": "123456"})
    data = res.json()
    return data["data"]["token"]