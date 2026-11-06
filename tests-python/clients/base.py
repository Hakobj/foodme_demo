import requests


def bearer(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


class BaseClient:
    """Shared plumbing: one `requests.Session` and the backend base URL."""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url

    def _get(self, path: str, token: str | None = None, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base_url}{path}", headers=bearer(token), **kwargs)

    def _post(self, path: str, json: dict | None = None, token: str | None = None, **kwargs) -> requests.Response:
        return self.session.post(f"{self.base_url}{path}", json=json, headers=bearer(token), **kwargs)
