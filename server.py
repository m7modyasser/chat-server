import socket
import threading
import tkinter as tk
from tkinter import scrolledtext

# ========================
# اتغير الـ IP ده لما تشتغل على AWS
# ========================
HOST = '0.0.0.0'   # على AWS: اتركه كده
PORT = 50000

client_conn = None  # الاتصال الحالي مع الكلاينت

def receive_messages(conn, chat_box):
    """Thread مستقل يستقبل الرسائل باستمرار"""
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                show_message(chat_box, "[System] Client disconnected.")
                break
            show_message(chat_box, f"Client: {data.decode()}")
        except:
            show_message(chat_box, "[System] Connection lost.")
            break

def send_message(entry, chat_box):
    """ترسل الرسالة للكلاينت"""
    global client_conn
    msg = entry.get().strip()
    if msg and client_conn:
        try:
            client_conn.sendall(msg.encode())
            show_message(chat_box, f"You: {msg}")
            entry.delete(0, tk.END)
        except:
            show_message(chat_box, "[System] Failed to send message.")

def show_message(chat_box, msg):
    """يضيف رسالة في الـ chat box"""
    chat_box.config(state=tk.NORMAL)
    chat_box.insert(tk.END, msg + "\n")
    chat_box.yview(tk.END)
    chat_box.config(state=tk.DISABLED)

def start_server(chat_box):
    """يشغّل السيرفر في thread مستقل"""
    global client_conn

    def run():
        global client_conn
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        show_message(chat_box, f"[System] Server listening on port {PORT}...")

        conn, addr = server_socket.accept()
        client_conn = conn
        show_message(chat_box, f"[System] Connected: {addr}")

        # thread لاستقبال الرسائل
        t = threading.Thread(target=receive_messages, args=(conn, chat_box), daemon=True)
        t.start()

    threading.Thread(target=run, daemon=True).start()

# ========================
# الـ UI
# ========================
root = tk.Tk()
root.title("Chat Server")
root.geometry("500x600")
root.resizable(False, False)
root.configure(bg="#1e1e2e")

# Chat box
chat_box = scrolledtext.ScrolledText(root, state=tk.DISABLED, wrap=tk.WORD,
                                      bg="#2a2a3d", fg="#e0e0e0",
                                      font=("Consolas", 11), bd=0)
chat_box.pack(padx=10, pady=(10, 5), fill=tk.BOTH, expand=True)

# Input frame
frame = tk.Frame(root, bg="#1e1e2e")
frame.pack(fill=tk.X, padx=10, pady=(0, 10))

entry = tk.Entry(frame, font=("Consolas", 11), bg="#2a2a3d", fg="white",
                 insertbackground="white", bd=0, relief=tk.FLAT)
entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 5))
entry.bind("<Return>", lambda e: send_message(entry, chat_box))

send_btn = tk.Button(frame, text="Send", bg="#5865f2", fg="white",
                     font=("Consolas", 11, "bold"), bd=0, relief=tk.FLAT,
                     padx=12, command=lambda: send_message(entry, chat_box))
send_btn.pack(side=tk.RIGHT)

# ابدأ السيرفر تلقائياً
start_server(chat_box)

root.mainloop()