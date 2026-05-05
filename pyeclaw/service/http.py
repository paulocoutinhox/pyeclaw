import shutil
import ssl
from pathlib import Path
from urllib.request import Request, urlopen

import certifi


class HttpClient:
    """http client with proper ssl certificate handling for frozen builds."""

    _ssl_context: ssl.SSLContext | None = None

    @classmethod
    def ssl_context(cls) -> ssl.SSLContext:
        """return a shared ssl context using certifi ca bundle."""
        if cls._ssl_context is None:
            cls._ssl_context = ssl.create_default_context(cafile=certifi.where())
        return cls._ssl_context

    @classmethod
    def get_json(cls, url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> bytes:
        """perform a GET request and return the response body as bytes."""
        req = Request(url, headers=headers or {})
        with urlopen(req, timeout=timeout, context=cls.ssl_context()) as resp:
            return resp.read()

    @classmethod
    def download(cls, url: str, dest: Path, timeout: int = 120):
        """download a file to disk."""
        req = Request(url, headers={"User-Agent": "PyeClaw"})
        with urlopen(req, timeout=timeout, context=cls.ssl_context()) as resp:
            with open(dest, "wb") as f:
                shutil.copyfileobj(resp, f)
