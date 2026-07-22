import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session = None


def session():
    """A process-wide requests session with sensible retries on flaky upstreams."""
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _session = s
    return _session
