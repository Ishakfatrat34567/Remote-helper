import json
import os
import platform
import random
import socket
import string
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

APP_PORT = 50555
BUFFER_SIZE = 4096


class RemoteAssistApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Consent-Based Remote Assistance")
        self.root.geometry("720x460")

        self.server_socket = None
        self.server_thread = None
        self.active_code = None

        self.status_var = tk.StringVar(value="Not listening")
        self.code_var = tk.StringVar(value="------")

        self.target_ip_var = tk.StringVar()
        self.target_code_var = tk.StringVar()
        self.helper_status_var = tk.StringVar(value="Idle")

        self._build_ui()

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=16, pady=16)

        host_frame = ttk.Frame(notebook)
        helper_frame = ttk.Frame(notebook)
        about_frame = ttk.Frame(notebook)

        notebook.add(host_frame, text="Share My PC (with consent)")
        notebook.add(helper_frame, text="Request to Help")
        notebook.add(about_frame, text="Safety")

        # Host tab
        ttk.Label(
            host_frame,
            text="Generate a one-time code and wait for a helper request.",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(host_frame, text="One-time code:").pack(anchor="w")
        ttk.Label(host_frame, textvariable=self.code_var, font=("Consolas", 24, "bold")).pack(
            anchor="w", pady=(0, 12)
        )

        ttk.Label(host_frame, textvariable=self.status_var, foreground="#1f6f43").pack(
            anchor="w", pady=(0, 12)
        )

        btn_row = ttk.Frame(host_frame)
        btn_row.pack(anchor="w")

        ttk.Button(btn_row, text="Start Listening", command=self.start_listening).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(btn_row, text="Stop", command=self.stop_listening).pack(side="left")

        ttk.Separator(host_frame).pack(fill="x", pady=16)

        ttk.Label(
            host_frame,
            text="After you approve a helper request, this app opens a trusted remote-support tool.",
            wraplength=640,
        ).pack(anchor="w")

        # Helper tab
        ttk.Label(
            helper_frame,
            text="Send a help request. The other person must explicitly approve.",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(helper_frame, text="Target IP address:").pack(anchor="w")
        ttk.Entry(helper_frame, textvariable=self.target_ip_var, width=36).pack(anchor="w", pady=(0, 10))

        ttk.Label(helper_frame, text="One-time code:").pack(anchor="w")
        ttk.Entry(helper_frame, textvariable=self.target_code_var, width=20).pack(anchor="w", pady=(0, 12))

        ttk.Button(helper_frame, text="Send Help Request", command=self.send_help_request).pack(anchor="w")

        ttk.Label(helper_frame, textvariable=self.helper_status_var, foreground="#2d4f8a").pack(
            anchor="w", pady=(12, 0)
        )

        # Safety tab
        safety_text = (
            "This demo is intentionally consent-based and visible.\n\n"
            "• No hidden background access\n"
            "• No persistence or auto-start\n"
            "• Every session requires explicit approval\n"
            "• Intended for legitimate support only\n"
        )
        ttk.Label(about_frame, text=safety_text, justify="left", wraplength=660).pack(
            anchor="w", pady=8
        )

    def start_listening(self):
        if self.server_socket:
            self.status_var.set("Already listening")
            return

        self.active_code = self._generate_code()
        self.code_var.set(self.active_code)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind(("0.0.0.0", APP_PORT))
            self.server_socket.listen(5)
        except OSError as exc:
            self.server_socket = None
            messagebox.showerror("Server error", f"Unable to listen on port {APP_PORT}:\n{exc}")
            return

        self.status_var.set(f"Listening on port {APP_PORT}. Share this code: {self.active_code}")

        self.server_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.server_thread.start()

    def stop_listening(self):
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        self.active_code = None
        self.code_var.set("------")
        self.status_var.set("Not listening")

    def _accept_loop(self):
        while self.server_socket:
            try:
                client, addr = self.server_socket.accept()
            except OSError:
                break

            threading.Thread(
                target=self._handle_client,
                args=(client, addr),
                daemon=True,
            ).start()

    def _handle_client(self, client: socket.socket, addr):
        with client:
            try:
                payload = client.recv(BUFFER_SIZE)
                data = json.loads(payload.decode("utf-8"))
            except Exception:
                return

            if data.get("code") != self.active_code:
                client.sendall(json.dumps({"ok": False, "reason": "invalid_code"}).encode("utf-8"))
                return

            helper_name = data.get("name", "Helper")
            helper_ip = addr[0]

            approved = self._ask_approval(helper_name, helper_ip)
            if not approved:
                client.sendall(json.dumps({"ok": False, "reason": "denied"}).encode("utf-8"))
                return

            client.sendall(json.dumps({"ok": True, "message": "approved"}).encode("utf-8"))
            self.root.after(0, self._launch_remote_support_tool)

    def _ask_approval(self, helper_name: str, helper_ip: str) -> bool:
        result = {"approved": False}
        done = threading.Event()

        def prompt():
            result["approved"] = messagebox.askyesno(
                "Approve helper?",
                f"{helper_name} ({helper_ip}) wants to start a remote support session.\n\n"
                "Allow this request?",
            )
            done.set()

        self.root.after(0, prompt)
        done.wait()
        return result["approved"]

    def send_help_request(self):
        host = self.target_ip_var.get().strip()
        code = self.target_code_var.get().strip().upper()

        if not host or not code:
            messagebox.showwarning("Missing data", "Please enter target IP and one-time code.")
            return

        self.helper_status_var.set("Sending request...")

        request_data = {
            "name": os.getenv("USERNAME") or os.getenv("USER") or "Helper",
            "code": code,
        }

        try:
            with socket.create_connection((host, APP_PORT), timeout=8) as sock:
                sock.sendall(json.dumps(request_data).encode("utf-8"))
                response = json.loads(sock.recv(BUFFER_SIZE).decode("utf-8"))
        except OSError as exc:
            self.helper_status_var.set(f"Connection failed: {exc}")
            return
        except json.JSONDecodeError:
            self.helper_status_var.set("Unexpected response from target")
            return

        if response.get("ok"):
            self.helper_status_var.set("Request approved. Ask them to share their support session link.")
            messagebox.showinfo(
                "Approved",
                "The user approved your request.\n\n"
                "Now continue in a trusted tool (Quick Assist / RustDesk / AnyDesk)",
            )
        else:
            reason = response.get("reason", "unknown")
            self.helper_status_var.set(f"Request rejected ({reason})")

    @staticmethod
    def _generate_code(length: int = 6) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(random.choice(alphabet) for _ in range(length))

    def _launch_remote_support_tool(self):
        system = platform.system().lower()

        if "windows" in system:
            try:
                subprocess.Popen(["cmd", "/c", "start", "ms-quick-assist:"], shell=False)
                self.status_var.set("Approved. Opened Quick Assist.")
                return
            except OSError:
                pass

        messagebox.showinfo(
            "Session approved",
            "Open your preferred trusted remote support tool (Quick Assist, RustDesk, AnyDesk)\n"
            "and share connection details only with people you trust.",
        )
        self.status_var.set("Approved. Launch your trusted support tool manually.")


if __name__ == "__main__":
    root = tk.Tk()
    app = RemoteAssistApp(root)
    root.protocol("WM_DELETE_WINDOW", app.stop_listening)
    root.mainloop()
