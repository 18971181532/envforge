"""EnvForge HTTP server — serves the web dashboard and API."""
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .store import Store
from .capture import capture_environment, summarize_profile
from .drift import detect_drift
from .compare import compare_profiles
from .graph import build_environment_graph, build_comparison_graph


WEB_DIR = Path(__file__).parent / "web"


class EnvForgeHandler(BaseHTTPRequestHandler):
    store = None
    base_dir = None

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type):
        try:
            with open(filepath, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._send_json({"error": "Not found"}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API routes
        if path == "/api/stats":
            self._send_json(self.store.stats())
            return

        if path == "/api/profiles":
            self._send_json(self.store.list_all())
            return

        if path == "/api/profile":
            name = params.get("name", [None])[0]
            if not name:
                self._send_json({"error": "name required"}, 400)
                return
            profile = self.store.get(name)
            if profile:
                self._send_json(profile)
            else:
                self._send_json({"error": "Profile not found"}, 404)
            return

        if path == "/api/graph":
            name = params.get("name", [None])[0]
            if not name:
                self._send_json({"error": "name required"}, 400)
                return
            profile = self.store.get(name)
            if profile:
                self._send_json(build_environment_graph(profile))
            else:
                self._send_json({"error": "Profile not found"}, 404)
            return

        if path == "/api/drift":
            name = params.get("name", [None])[0]
            if not name:
                self._send_json({"error": "name required"}, 400)
                return
            profile = self.store.get(name)
            if profile:
                self._send_json(detect_drift(profile))
            else:
                self._send_json({"error": "Profile not found"}, 404)
            return

        if path == "/api/compare":
            a = params.get("a", [None])[0]
            b = params.get("b", [None])[0]
            if not a or not b:
                self._send_json({"error": "a and b required"}, 400)
                return
            pa = self.store.get(a)
            pb = self.store.get(b)
            if pa and pb:
                self._send_json(compare_profiles(pa, pb))
            else:
                self._send_json({"error": "Profile not found"}, 404)
            return

        if path == "/api/compare-graph":
            a = params.get("a", [None])[0]
            b = params.get("b", [None])[0]
            if not a or not b:
                self._send_json({"error": "a and b required"}, 400)
                return
            pa = self.store.get(a)
            pb = self.store.get(b)
            if pa and pb:
                self._send_json(build_comparison_graph(pa, pb))
            else:
                self._send_json({"error": "Profile not found"}, 404)
            return

        if path == "/api/history":
            name = params.get("name", [None])[0]
            if not name:
                self._send_json({"error": "name required"}, 400)
                return
            self._send_json({"history": self.store.history(name)})
            return

        if path == "/api/capture":
            name = params.get("name", ["web_capture"])[0]
            profile = capture_environment(name=name)
            self.store.save(profile)
            self._send_json(summarize_profile(profile))
            return

        # Static files
        if path == "/" or path == "/index.html":
            self._send_file(str(WEB_DIR / "index.html"), "text/html; charset=utf-8")
            return
        if path == "/style.css":
            self._send_file(str(WEB_DIR / "style.css"), "text/css; charset=utf-8")
            return
        if path == "/app.js":
            self._send_file(str(WEB_DIR / "app.js"), "application/javascript; charset=utf-8")
            return

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/capture":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b"{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {}
            name = data.get("name", "web_capture")
            profile = capture_environment(name=name)
            self.store.save(profile)
            self._send_json(summarize_profile(profile))
            return

        if path == "/api/delete":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b"{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {}
            name = data.get("name", "")
            if name and self.store.delete(name):
                self._send_json({"deleted": name})
            else:
                self._send_json({"error": "Profile not found"}, 404)
            return

        self._send_json({"error": "Not found"}, 404)


def start_server(base_dir=None, port=8765, host="127.0.0.1"):
    store = Store(base_dir or os.getcwd())
    if not store.is_initialized():
        store.init()

    handler = EnvForgeHandler
    handler.store = store
    handler.base_dir = base_dir or os.getcwd()

    server = HTTPServer((host, port), handler)
    print(f"EnvForge dashboard running at http://{host}:{port}")
    print(f"Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.server_close()
