#!/usr/bin/env python3
"""Genera informe_temp.pdf desde informe.html via Chrome DevTools Protocol.
displayHeaderFooter=False garantiza que no aparezca ningún pie de página."""

import os, sys, time, json, base64, subprocess, urllib.request, urllib.error
import websocket

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML       = f"file://{SCRIPT_DIR}/informe.html"
OUTPUT     = f"{SCRIPT_DIR}/informe_temp.pdf"
PORT       = 9224

def wait_for_cdp(port, retries=40):
    for _ in range(retries):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/json/version") as r:
                json.loads(r.read())
                return True
        except Exception:
            continue
    return False

def cdp_call(ws, method, params=None, msg_id=1):
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        raw = ws.recv()
        msg = json.loads(raw)
        if msg.get("id") == msg_id:
            return msg

def main():
    print("Iniciando Chrome...")
    proc = subprocess.Popen(
        [
            "google-chrome",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-extensions",
            "--disable-background-networking",
            f"--remote-debugging-port={PORT}",
            "--remote-allow-origins=*",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        if not wait_for_cdp(PORT):
            print("Error: Chrome no respondió en el puerto CDP.", file=sys.stderr)
            sys.exit(1)

        # Obtener target de la pestaña
        with urllib.request.urlopen(f"http://localhost:{PORT}/json") as r:
            targets = json.loads(r.read())

        page_targets = [t for t in targets if t.get("type") == "page"]
        if not page_targets:
            print("Error: no se encontró target de tipo page.", file=sys.stderr)
            sys.exit(1)

        ws_url = page_targets[0]["webSocketDebuggerUrl"]
        ws = websocket.create_connection(ws_url, timeout=30)

        # Habilitar dominio Page y navegar
        cdp_call(ws, "Page.enable", msg_id=1)
        cdp_call(ws, "Page.navigate", {"url": HTML}, msg_id=2)

        # Esperar carga real
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                ws.settimeout(0.5)
                msg = json.loads(ws.recv())
                if msg.get("method") in ("Page.loadEventFired", "Page.frameStoppedLoading"):
                    break
            except Exception:
                pass
        ws.settimeout(30)
        time.sleep(1)

        # Generar PDF sin header/footer
        result = cdp_call(ws, "Page.printToPDF", {
            "displayHeaderFooter": False,
            "printBackground":     True,
            "paperWidth":          8.27,
            "paperHeight":        11.69,
            "marginTop":           0.55,
            "marginBottom":        0.55,
            "marginLeft":          0.63,
            "marginRight":         0.63,
        }, msg_id=3)

        ws.close()

        if "error" in result:
            print(f"Error CDP: {result['error']}", file=sys.stderr)
            sys.exit(1)

        pdf_bytes = base64.b64decode(result["result"]["data"])
        with open(OUTPUT, "wb") as f:
            f.write(pdf_bytes)

        print(f"Listo: {OUTPUT} ({len(pdf_bytes) // 1024} KB)")

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
