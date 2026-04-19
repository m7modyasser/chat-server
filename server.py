import socket
import threading
import os

HOST = '0.0.0.0'
PORT = int(os.environ.get("PORT", 50000))

clients = []  # قايمة الكلاينتس المتصلين

def handle_client(conn, addr):
    print(f"[+] Connected: {addr}")
    clients.append(conn)
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            msg = data.decode()
            print(f"[{addr}]: {msg}")
            # ابعت الرسالة لكل الكلاينتس التانيين
            for c in clients:
                if c != conn:
                    try:
                        c.sendall(f"[{addr[0]}]: {msg}".encode())
                    except:
                        pass
        except:
            break
    print(f"[-] Disconnected: {addr}")
    clients.remove(conn)
    conn.close()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
print(f"[Server] Listening on port {PORT}...")

while True:
    conn, addr = server_socket.accept()
    t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
    t.start()
