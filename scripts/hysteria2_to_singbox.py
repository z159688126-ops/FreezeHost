#!/usr/bin/env python3
"""Generate sing-box config from a Hysteria2 share URI.

Input env:
  FREEZEHOST_HYSTERIA2_URI = hysteria2://password@host:port?sni=...&alpn=h3&insecure=1
Output:
  sing-box-hysteria2.json
"""
import json
import os
import sys
from urllib.parse import parse_qs, unquote, urlparse

uri = os.environ.get("FREEZEHOST_HYSTERIA2_URI", "").strip()
if not uri:
    print("缺少 FREEZEHOST_HYSTERIA2_URI", file=sys.stderr)
    sys.exit(2)

u = urlparse(uri)
if u.scheme.lower() not in {"hysteria2", "hy2"}:
    print(f"不支持的协议: {u.scheme}", file=sys.stderr)
    sys.exit(2)
if not u.hostname or not u.port:
    print("节点链接缺少服务器地址或端口", file=sys.stderr)
    sys.exit(2)

q = parse_qs(u.query)
password = unquote(u.username or "")
if not password:
    print("节点链接缺少密码/UUID", file=sys.stderr)
    sys.exit(2)

sni = (q.get("sni") or q.get("peer") or [u.hostname])[0]
insecure_raw = (q.get("insecure") or q.get("allowInsecure") or ["0"])[0]
insecure = str(insecure_raw).lower() in {"1", "true", "yes"}
alpn_raw = (q.get("alpn") or [""])[0]
alpn = [x.strip() for x in alpn_raw.split(",") if x.strip()]

outbound = {
    "type": "hysteria2",
    "tag": "proxy",
    "server": u.hostname,
    "server_port": int(u.port),
    "password": password,
    "tls": {
        "enabled": True,
        "server_name": sni,
        "insecure": insecure,
    },
}
if alpn:
    outbound["tls"]["alpn"] = alpn

# Optional bandwidth parameters. Hysteria2 can work without them in sing-box.
for key, out_key in (("upmbps", "up_mbps"), ("downmbps", "down_mbps")):
    val = (q.get(key) or q.get(key.replace("mbps", "Mbps")) or [""])[0]
    if val:
        try:
            outbound[out_key] = int(float(val))
        except ValueError:
            pass

config = {
    "log": {"level": "info", "timestamp": True},
    "inbounds": [
        {
            "type": "socks",
            "tag": "socks-in",
            "listen": "127.0.0.1",
            "listen_port": 10808,
        }
    ],
    "outbounds": [outbound, {"type": "direct", "tag": "direct"}],
    "route": {"final": "proxy"},
}

with open("sing-box-hysteria2.json", "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("已生成 sing-box-hysteria2.json，代理监听 socks5://127.0.0.1:10808")
