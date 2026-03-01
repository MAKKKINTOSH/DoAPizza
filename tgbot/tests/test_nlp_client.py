from tgbot.nlp_client import _normalize_local_base_url


def test_normalize_local_base_url_rewrites_zero_address() -> None:
    assert _normalize_local_base_url("http://0.0.0.0:8182") == "http://127.0.0.1:8182"


def test_normalize_local_base_url_keeps_normal_host() -> None:
    assert _normalize_local_base_url("http://127.0.0.1:8182") == "http://127.0.0.1:8182"
