import ipaddress
import socket
import re
from urllib.parse import urlparse
from fastapi import HTTPException

ALLOWED_GITHUB_HOSTS = {"github.com", "raw.githubusercontent.com", "api.github.com"}


def is_ip_private_or_loopback(ip_str: str) -> bool:
    """Checks if an IP string is loopback, private RFC1918, link-local, or multicast."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast:
            return True
        if ip.is_reserved:
            # Handle NAT64 well-known prefix (64:ff9b::/96) by validating embedded IPv4
            if ip.version == 6 and str(ip).startswith("64:ff9b:"):
                embedded_ipv4 = ipaddress.IPv4Address(ip.packed[12:16])
                return embedded_ipv4.is_loopback or embedded_ipv4.is_private or embedded_ipv4.is_link_local
            return True
        return False
    except ValueError:
        return True


def validate_github_url(url: str) -> dict:
    """
    Strict SSRF-hardened GitHub URL validator.
    Ensures:
    1. HTTPS scheme only
    2. Host is github.com (or official github domain)
    3. Host IP DNS resolution does NOT map to loopback, RFC1918, link-local, or private ranges
    4. Rejects file://, javascript:, data:, IP literals, localhost, and non-443 ports
    5. Returns parsed (repo_url, release_tag, version, asset_name)
    """
    if not url or not isinstance(url, str):
        raise HTTPException(400, "URL must be a non-empty string")

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme.lower() != "https":
        raise HTTPException(400, "Only HTTPS GitHub URLs are permitted")

    hostname = (parsed.hostname or "").lower()
    if not hostname or hostname not in ALLOWED_GITHUB_HOSTS:
        raise HTTPException(400, f"Host '{hostname}' is not a permitted GitHub domain")

    if parsed.port and parsed.port != 443:
        raise HTTPException(400, "Custom ports are not permitted")

    # Resolve IP and verify against SSRF private/loopback ranges
    try:
        ip_addresses = socket.getaddrinfo(hostname, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, socktype, proto, canonname, sockaddr in ip_addresses:
            ip_str = sockaddr[0]
            if is_ip_private_or_loopback(ip_str):
                raise HTTPException(400, f"Resolved IP address '{ip_str}' is blocked due to security rules")
    except socket.gaierror:
        raise HTTPException(400, f"Failed to resolve DNS for hostname '{hostname}'")

    # Extract repository path, release tag, and asset filename if present
    # Pattern e.g. https://github.com/owner/repo/releases/download/v1.2.0/Asset.vmte
    # or https://github.com/owner/repo/tree/v1.2.0
    path = parsed.path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise HTTPException(400, "GitHub URL must include owner and repository name")

    owner, repo = parts[0], parts[1]
    repo_url = f"https://github.com/{owner}/{repo}"

    release_tag = ""
    asset_name = ""

    if "releases/tag/" in url:
        release_tag = url.split("releases/tag/")[-1].split("/")[0]
    elif "releases/download/" in url:
        dl_parts = url.split("releases/download/")[-1].split("/")
        if len(dl_parts) >= 1:
            release_tag = dl_parts[0]
        if len(dl_parts) >= 2:
            asset_name = dl_parts[1]
    elif len(parts) >= 4 and parts[2] == "releases":
        release_tag = parts[3]

    clean_version = release_tag.lstrip("vV") if release_tag else "1.0.0"

    return {
        "repository_url": repo_url,
        "owner": owner,
        "repo": repo,
        "release_tag": release_tag or "v1.0.0",
        "submitted_version": clean_version,
        "asset_name": asset_name
    }
