#!/usr/bin/env python3
"""Simple bridge subscription server."""

import os
from flask import Flask, Response

app = Flask(__name__)

SUBSCRIPTION_FILE = "/opt/marznode/subscriptions/bridge.txt"


def get_subscription():
    """Read subscription from file or env."""
    if os.path.exists(SUBSCRIPTION_FILE):
        with open(SUBSCRIPTION_FILE, "r") as f:
            return f.read().strip()
    return os.environ.get("BRIDGE_LINK", "")


@app.route("/sub/bridge/")
def bridge_subscription():
    sub = get_subscription()
    if not sub:
        return "No bridge subscription configured", 404
    return Response(
        sub,
        mimetype="text/plain",
        headers={
            "Content-Disposition": 'attachment; filename="bridge"',
            "Profile-Update-Interval": "60",
        },
    )


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)
