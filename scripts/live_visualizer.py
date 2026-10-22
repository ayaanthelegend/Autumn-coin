"""Guaranteed Instant Real-Time 2D Physics Visualizer Launcher.

Launches the 60 FPS interactive physics visualizer on Windows / Linux / macOS.
Single command:
    python scripts/live_visualizer.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn

ROOT_DIR = Path(__file__).resolve().parent.parent
HTML_PATH = ROOT_DIR / "visualizer.html"
FRAMES_DIR = ROOT_DIR / "results_sph" / "frames"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PORT = 8000


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class VisualizerRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        # Route root requests to visualizer.html
        clean_path = path.split("?")[0].split("#")[0]
        if clean_path in ("/", "/index.html"):
            return str(HTML_PATH)
        return str(ROOT_DIR / clean_path.lstrip("/"))

    def do_POST(self):
        if self.path == "/api/save_screenshot":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
                img_data_url = data.get("image", "")
                if "," in img_data_url:
                    img_data_url = img_data_url.split(",")[1]

                img_bytes = base64.b64decode(img_data_url)
                timestamp = int(time.time())
                mode_str = "ode" if data.get("mode", 0) == 0 else "sph"
                i_star_str = f"I{float(data.get('I_star', 0.68)):.2f}"
                out_filename = f"screenshot_{mode_str}_{i_star_str}_{timestamp}.png"
                out_path = FRAMES_DIR / out_filename

                with open(out_path, "wb") as f:
                    f.write(img_bytes)

                resp = json.dumps({"status": "ok", "filename": str(out_path.name)})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(resp.encode("utf-8"))
                print(f"[Visualizer Server] Saved screenshot: {out_path}")
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Silence standard HTTP access logs for clean console
        pass


def run_visualizer(port: int = DEFAULT_PORT, open_browser: bool = True):
    # Check if native C++ viewer was requested
    if "--native" in sys.argv or "--cpp" in sys.argv:
        cpp_exe = ROOT_DIR / "cpp_sph" / "bin" / "sph_viewer.exe"
        if cpp_exe.exists():
            print(f"[Visualizer] Launching Native C++20 Win32 Viewer: {cpp_exe}")
            os.system(f'"{cpp_exe}"')
            return
        else:
            print(f"[Visualizer] Native executable {cpp_exe} not found. Launching instant WebGL visualizer...")

    server_address = ("", port)
    for p in range(port, port + 20):
        try:
            httpd = ThreadedHTTPServer(("", p), VisualizerRequestHandler)
            port = p
            break
        except OSError:
            continue

    url = f"http://localhost:{port}/"

    print("=" * 68)
    print("   AUTUMN COIN: REAL-TIME 2D PHYSICS VISUALIZER (60 FPS)")
    print("   Sebastian Lague Style | Clean White Background (#FFFFFF)")
    print("=" * 68)
    print(f" • Dashboard URL:         {url}")
    print(f" • Native C++ Executable: {ROOT_DIR / 'cpp_sph' / 'bin' / 'sph_viewer.exe'}")
    print(" • Mode A:                2D Quasi-Steady ODE (Andersen 2005b)")
    print(" • Mode B:                2D WCSPH-FSI (Wendland C2 + Akinci Coupling)")
    print("-" * 68)
    print(" Controls:")
    print("   [Tab]  Toggle Mode A (ODE) / Mode B (SPH)")
    print("   [1]    Steady Descent Preset (I* = 0.06)")
    print("   [2]    Periodic Fluttering Preset (I* = 0.68)")
    print("   [3]    Clean Tumbling Preset (I* = 1.20)")
    print("   [4]    Chaotic / Mixed Preset (I* = 3.50)")
    print("   [Space] Pause / Resume")
    print("   [S]    Step 1 Frame")
    print("   [R]    Reset Drop")
    print("   [E]    Toggle 15-Coin Ensemble Mode (watch chaotic divergence live!)")
    print("   [C]    Cycle Particle Coloring (Speed / Vorticity / Pressure)")
    print("   [P]    Save 300 DPI PNG Screenshot")
    print("=" * 68)
    print("Press Ctrl+C to terminate the visualizer server.")

    if open_browser:
        webbrowser.open_new_tab(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Visualizer] Server stopped.")
        httpd.server_close()


if __name__ == "__main__":
    run_visualizer()
