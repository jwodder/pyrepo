import json
import requests

ACCEPT = 'application/vnd.github.v3+json'

API_ENDPOINT = 'https://api.github.com'

class GitHub:
    def __init__(self, url=API_ENDPOINT, session=None, _method=None):
        self._url = url
        if session is None:
            session = requests.Session()
            session.headers["Accept"] = ACCEPT
        self._session = session
        self._method = _method

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, name):
        url = self._url
        if self._method is not None:
            p = str(self._method)
            if p.lower().startswith(('http://', 'https://')):
                url = p
            else:
                url = url.rstrip('/') + '/' + p.lstrip('/')
        return GitHub(url=url, session=self._session, _method=name)

    def __call__(self, raw=False, **kwargs):
        r = self._session.request(self._method, self._url, **kwargs)
        if raw:
            return r
        elif not r.ok:
            raise GitHubException(r)
        elif self._method.lower() == 'get' and 'next' in r.links:
            return paginate(self._session, r)
        elif r.status_code == 204:
            return None
        else:
            return r.json()


class GitHubException(Exception):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        if 400 <= self.response.status_code < 500:
            msg = '{0.status_code} Client Error: {0.reason} for url: {0.url}\n'
        elif 500 <= self.response.status_code < 600:
            msg = '{0.status_code} Server Error: {0.reason} for url: {0.url}\n'
        else:
            msg = '{0.status_code} Unknown Error: {0.reason} for url: {0.url}\n'
        msg = msg.format(self.response)
        try:
            resp = self.response.json()
        except ValueError:
            msg += self.response.text
        else:
            msg += json.dumps(resp, sort_keys=True, indent=4)
        return msg


def paginate(session, r):
    while True:
        if not r.ok:
            raise GitHubException(r)
        yield from r.json()
        url = r.links.get('next', {}).get('url')
        if url is None:
            break
        r = session.get(url)
