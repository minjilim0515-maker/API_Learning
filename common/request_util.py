import requests
class RequestUtil:
    @staticmethod
    def send_request(method, url, **kwargs):
        res = requests.request(method=method, url=url, **kwargs)
        return res.json()
    