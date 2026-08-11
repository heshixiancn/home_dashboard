import ipaddress
import re
from urllib.parse import urlparse, urlunparse

from pydantic import ValidationError

HOST_RE = re.compile(r"^(?=.{1,253}$)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")


class UrlValueError(ValueError):
    pass


def validate_host(host: str) -> str:
    value = host.strip()
    if not value:
        raise UrlValueError("host is required")
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if not HOST_RE.match(value):
        raise UrlValueError("host must be an IPv4/IPv6 address or valid hostname")
    return value


def normalize_path(path: str | None) -> str:
    if not path:
        return "/"
    value = path.strip()
    if not value.startswith("/"):
        value = "/" + value
    return value


def validate_protocol(protocol: str) -> str:
    value = protocol.lower().strip()
    if value not in {"http", "https"}:
        raise UrlValueError("only http and https are allowed")
    return value


def validate_port(port: int | None) -> int | None:
    if port is None:
        return None
    if port < 1 or port > 65535:
        raise UrlValueError("port must be between 1 and 65535")
    return port


def validate_http_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UrlValueError("only http and https URLs are allowed")
    if not parsed.hostname:
        raise UrlValueError("URL host is required")
    validate_host(parsed.hostname)
    if parsed.port is not None:
        validate_port(parsed.port)
    if parsed.username or parsed.password:
        raise UrlValueError("credentials in URLs are not allowed")
    path = parsed.path or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, parsed.fragment))


def build_service_url(*, protocol: str, host: str, port: int | None, path: str | None, custom_url: str | None = None) -> str:
    if custom_url and custom_url.strip():
        return validate_http_url(custom_url)
    scheme = validate_protocol(protocol)
    clean_host = validate_host(host)
    clean_port = validate_port(port)
    clean_path = normalize_path(path)
    netloc = f"[{clean_host}]" if ":" in clean_host and not clean_host.startswith("[") else clean_host
    if clean_port:
        netloc = f"{netloc}:{clean_port}"
    return urlunparse((scheme, netloc, clean_path, "", "", ""))

