"""Временный прокси на server-2 (разрешён Анваром 26.10): пропускает к Ollama (ssh-туннель с Mac на 127.0.0.1:11435)
только запросы с заголовком Authorization: Bearer <ключ из ~/ollama-bridge/key>. Поток передаётся кусками."""
import http.client, http.server, os, socketserver
KEY = open(os.path.expanduser("~/ollama-bridge/key")).read().strip()
class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def _go(self):
        if self.headers.get("Authorization", "") != "Bearer " + KEY:
            self.send_response(401); self.send_header("Content-Length", "0"); self.end_headers(); return
        body = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        c = http.client.HTTPConnection("127.0.0.1", 11435, timeout=1800)
        c.request(self.command, self.path, body=body, headers={"Content-Type": self.headers.get("Content-Type", "application/json")})
        r = c.getresponse()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"): self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked"); self.end_headers()
        while True:
            chunk = r.read1(65536)
            if not chunk: break
            self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk)); self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
    do_GET = do_POST = _go
    def log_message(self, *a): pass
class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True
S(("0.0.0.0", 18443), H).serve_forever()
