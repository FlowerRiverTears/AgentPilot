"""SSRF protection utilities for outbound HTTP requests."""
import ipaddress
import re
from urllib.parse import urlparse

# Private/internal IP ranges that should be blocked
PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local (AWS metadata)
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
]

# Hostnames that should be blocked
BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}


def is_url_safe(url: str) -> tuple[bool, str]:
    """Check if a URL is safe to request (not pointing to internal resources).

    Returns (is_safe, reason) tuple.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname in URL"

    # Check blocked hostnames
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False, f"Hostname '{hostname}' is blocked"

    # Check if hostname is an IP address in private ranges
    try:
        ip = ipaddress.ip_address(hostname)
        for network in PRIVATE_NETWORKS:
            if ip in network:
                return False, f"IP address {ip} is in private network range"
    except ValueError:
        pass  # Not an IP address, that's OK (it's a domain name)

    # Only allow http and https schemes
    if parsed.scheme not in ("http", "https"):
        return False, f"Scheme '{parsed.scheme}' is not allowed"

    return True, ""
