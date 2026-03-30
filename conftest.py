import pytest
from common.request_util import RequestUtil
@pytest.fixture(scope="module")
def login():
    res = RequestUtil("post","url", json={"username": "test", "password": "123456"})
    data = res.json()
    assert res.status_code == 200
    assert data["code" ] == 0
    return data["data"]["token"]