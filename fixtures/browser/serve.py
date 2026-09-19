#!/usr/bin/env python3
"""Minimal local TodoMVC-style fixture for browser/tool workflow tests.

Serves one page with an input + Add button, a list, and a counter, all wired by
plain JS in the page. No external assets, so it works fully offline.

    python3 serve.py            # serves on 127.0.0.1:8123
"""
import http.server
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8123

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>TodoMVC (mini)</title></head>
<body>
<h1>todos</h1>
<input id="new-todo" placeholder="What needs to be done?" />
<button id="add">Add</button>
<ul id="list"></ul>
<p>remaining: <span id="count">0</span></p>
<script>
const input = document.getElementById('new-todo');
const list = document.getElementById('list');
const count = document.getElementById('count');
let items = [];
function render() {
  list.innerHTML = '';
  for (const t of items) {
    const li = document.createElement('li');
    li.textContent = t;
    list.appendChild(li);
  }
  count.textContent = String(items.length);
}
document.getElementById('add').addEventListener('click', () => {
  const v = input.value.trim();
  if (!v) return;
  items.push(v);
  input.value = '';
  render();
});
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('add').click();
});
render();
</script>
</body></html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"serving TodoMVC fixture on http://127.0.0.1:{PORT}", flush=True)
        httpd.serve_forever()
