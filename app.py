"""
Flask site that gets an iPhone/iPad UDID.

How it works:
1. User opens "/" in Safari on their iOS device and taps "Install Profile".
2. Server sends a .mobileconfig (Profile Service payload).
3. After the user installs it in Settings, iOS POSTs a signed plist
   (containing UDID, PRODUCT, VERSION, ...) to /enroll.
4. Server extracts the plist, then redirects (HTTP 301) to /result.

Requirements:
    pip install flask

Run:
    BASE_URL=https://your-domain.com python app.py

NOTE: iOS requires HTTPS. For local testing use a tunnel, e.g.:
    ngrok http 5000   ->  BASE_URL=https://xxxx.ngrok-free.app
"""
import os
import plistlib
from html import escape
from urllib.parse import quote

from flask import Flask, Response, redirect, request

app = Flask(__name__)

BASE_URL = os.environ.get("BASE_URL", "https://udidkh.vercel.app").rstrip("/")

MOBILECONFIG = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <dict>
        <key>URL</key>
        <string>{BASE_URL}/enroll</string>
        <key>DeviceAttributes</key>
        <array>
            <string>UDID</string>
            <string>IMEI</string>
            <string>ICCID</string>
            <string>VERSION</string>
            <string>PRODUCT</string>
        </array>
    </dict>
    <key>PayloadOrganization</key>
    <string>My Company</string>
    <key>PayloadDisplayName</key>
    <string>Get Device UDID</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
    <key>PayloadUUID</key>
    <string>9CF421B3-9853-4454-BC8A-982CBD3C907C</string>
    <key>PayloadIdentifier</key>
    <string>com.example.udid.profile</string>
    <key>PayloadDescription</key>
    <string>This profile lets the website read your device UDID. It does not change any settings.</string>
    <key>PayloadType</key>
    <string>Profile Service</string>
</dict>
</plist>
"""


@app.route("/")
def index():
    return """
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Get UDID</title>
        <style>
            body { font-family: -apple-system, sans-serif; text-align: center; padding: 60px 20px; }
            a.btn { display: inline-block; padding: 14px 28px; background: #007aff;
                    color: #fff; border-radius: 12px; text-decoration: none; font-size: 18px; }
            p { color: #555; max-width: 420px; margin: 20px auto; }
        </style>
    </head>
    <body>
        <h1>Get your UDID</h1>
        <p>Open this page in <b>Safari</b> on your iPhone/iPad, tap the button,
           then go to <b>Settings → Profile Downloaded → Install</b>.</p>
        <a class="btn" href="/profile.mobileconfig">Install Profile</a>
    </body>
    </html>
    """


@app.route("/profile.mobileconfig")
def profile():
    return Response(
        MOBILECONFIG,
        mimetype="application/x-apple-aspen-config",
        headers={"Content-Disposition": "attachment; filename=udid.mobileconfig"},
    )


@app.route("/enroll", methods=["POST"])
def enroll():
    # Body is a PKCS#7-signed blob that wraps an XML plist.
    # We only need the plist, so slice it out.
    data = request.get_data()
    start = data.find(b"<?xml")
    end = data.find(b"</plist>")
    if start == -1 or end == -1:
        return "Invalid payload", 400

    info = plistlib.loads(data[start : end + len(b"</plist>")])

    udid = info.get("UDID", "")
    product = info.get("PRODUCT", "")
    version = info.get("VERSION", "")

    # iOS requires a 301 here so Safari opens the result page with GET.
    return redirect(
        f"/result?udid={quote(udid)}&product={quote(product)}&version={quote(version)}",
        code=301,
    )


@app.route("/result")
def result():
    udid = escape(request.args.get("udid", ""))
    product = escape(request.args.get("product", ""))
    version = escape(request.args.get("version", ""))
    return f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Your UDID</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; text-align: center; padding: 60px 20px; }}
            code {{ display: block; word-break: break-all; background: #f2f2f7;
                    padding: 16px; border-radius: 12px; margin: 20px auto; max-width: 480px; }}
            button {{ padding: 12px 24px; font-size: 16px; border-radius: 10px;
                      border: none; background: #007aff; color: #fff; }}
        </style>
    </head>
    <body>
        <h1>Your UDID</h1>
        <code id="udid">{udid}</code>
        <button onclick="navigator.clipboard.writeText(document.getElementById('udid').innerText)">Copy</button>
        <p>Device: {product} &middot; iOS {version}</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
