"""Local Flask dashboard app (cmd: serve)."""
import os
import json
import datetime as dt

from .excel_io import data_excel_path, read_portfolio_excel
from .template import load_html_template


def cmd_serve(args):
    from flask import Flask, Response, jsonify
    app = Flask(__name__)

    def current_html():
        p = data_excel_path()
        if os.path.exists(p):
            try:
                data = read_portfolio_excel(p)
            except Exception as e:
                data = {"meta": {"error": f"Could not read {p}: {e}"}, "epics": []}
        else:
            data = {"meta": {"error": "No Excel data yet. Run Sync first."}, "epics": []}
        data.setdefault("meta", {})["servedAt"] = dt.datetime.now().strftime("%H:%M")
        return load_html_template().replace("/*__DATA__*/null", json.dumps(data)).replace("/*__SERVED__*/false", "true")

    @app.route("/")
    def index():
        resp = Response(current_html(), mimetype="text/html")
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        return resp

    @app.route("/api/info")
    def info():
        return jsonify({"data": data_excel_path(), "time": dt.datetime.now().strftime("%H:%M:%S")})

    print(f"[serve] http://127.0.0.1:{args.port}  (data {data_excel_path()})")
    app.run(host="127.0.0.1", port=args.port, debug=False)
