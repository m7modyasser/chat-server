import socket
import threading
import os

# ========================
# Server Config
# ========================
HOST = '0.0.0.0'
PORT = int(os.environ.get("PORT", 50000))

clients = []        # List of (conn, addr, username) tuples
clients_lock = threading.Lock()  # NEW: Thread-safe access to clients list


# ========================
# Broadcast to all other clients
# NEW: Uses lock for thread safety + sends to everyone except sender
# ========================
def broadcast(data, sender_conn):
    with clients_lock:
        for (conn, addr, uname) in clients:
            if conn != sender_conn:
                try:
                    conn.sendall(data)
                except:
                    pass


# ========================
# Handle each client in its own thread
# From: server.py (original) — extended with file/image protocol
# ========================
def handle_client(conn, addr):
    username = f"User_{addr[1]}"  # Default username

    print(f"[+] Connected: {addr}")
    with clients_lock:
        clients.append((conn, addr, username))

    buffer = b""

    while True:
        try:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buffer += chunk

            # ========================
            # Protocol parsing loop
            # NEW: Custom protocol — no direct file size sending allowed per project rules.
            # We use header lines: "TEXT:<username>\n<msg>\n"
            #                      "IMAGE:<username>:<size>\n<bytes>"
            #                      "FILE:<username>:<filename>:<size>\n<bytes>"
            #                      "NAME:<username>\n"
            # ========================
            while buffer:
                # --- NAME protocol ---
                if buffer.startswith(b"NAME:"):
                    nl = buffer.find(b"\n")
                    if nl == -1:
                        break
                    line = buffer[:nl].decode(errors='replace')
                    username = line[5:].strip()
                    buffer = buffer[nl+1:]
                    # Update username in clients list
                    with clients_lock:
                        for i, (c, a, u) in enumerate(clients):
                            if c == conn:
                                clients[i] = (c, a, username)
                                break
                    print(f"[Name] {addr} => {username}")
                    # Announce join
                    join_msg = f"SYS:{username} joined the chat\n".encode()
                    broadcast(join_msg, conn)

                # --- TEXT protocol ---
                elif buffer.startswith(b"TEXT:"):
                    nl = buffer.find(b"\n")
                    if nl == -1:
                        break
                    line = buffer[:nl].decode(errors='replace')
                    # TEXT:<username>\n then next \n ends message
                    # Format: TEXT:<username>\n<message>\n
                    uname_part = line[5:]
                    buffer = buffer[nl+1:]
                    # Now read message until \n
                    nl2 = buffer.find(b"\n")
                    if nl2 == -1:
                        break
                    msg = buffer[:nl2].decode(errors='replace')
                    buffer = buffer[nl2+1:]
                    print(f"[MSG] {uname_part}: {msg}")
                    out = f"TEXT:{uname_part}\n{msg}\n".encode()
                    broadcast(out, conn)

                # --- IMAGE protocol ---
                elif buffer.startswith(b"IMAGE:"):
                    nl = buffer.find(b"\n")
                    if nl == -1:
                        break
                    header = buffer[:nl].decode(errors='replace')
                    # IMAGE:<username>:<size>
                    parts = header.split(":")
                    if len(parts) < 3:
                        buffer = buffer[nl+1:]
                        break
                    uname_part = parts[1]
                    size = int(parts[2])
                    total_needed = nl + 1 + size
                    if len(buffer) < total_needed:
                        break
                    img_data = buffer[nl+1 : total_needed]
                    buffer = buffer[total_needed:]
                    print(f"[IMG] {uname_part}: {size} bytes")
                    # Rebroadcast same protocol so clients can decode
                    out_header = f"IMAGE:{uname_part}:{size}\n".encode()
                    broadcast(out_header + img_data, conn)

                # --- FILE protocol ---
                elif buffer.startswith(b"FILE:"):
                    nl = buffer.find(b"\n")
                    if nl == -1:
                        break
                    header = buffer[:nl].decode(errors='replace')
                    # FILE:<username>:<filename>:<size>
                    parts = header.split(":", 3)
                    if len(parts) < 4:
                        buffer = buffer[nl+1:]
                        break
                    uname_part = parts[1]
                    filename = parts[2]
                    size = int(parts[3])
                    total_needed = nl + 1 + size
                    if len(buffer) < total_needed:
                        break
                    file_data = buffer[nl+1 : total_needed]
                    buffer = buffer[total_needed:]
                    print(f"[FILE] {uname_part}: {filename} ({size} bytes)")
                    out_header = f"FILE:{uname_part}:{filename}:{size}\n".encode()
                    broadcast(out_header + file_data, conn)

                else:
                    # Unknown protocol data — discard up to next newline
                    nl = buffer.find(b"\n")
                    if nl == -1:
                        buffer = b""
                        break
                    buffer = buffer[nl+1:]

        except Exception as e:
            print(f"[!] Error from {addr}: {e}")
            break

    # Cleanup
    print(f"[-] Disconnected: {addr} ({username})")
    with clients_lock:
        clients[:] = [(c, a, u) for (c, a, u) in clients if c != conn]
    conn.close()
    leave_msg = f"SYS:{username} left the chat\n".encode()
    broadcast(leave_msg, None)


# ========================
# Start the server
# From: server.py (original)
# ========================
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(10)
print(f"[Server] Listening on port {PORT}...")

while True:
    conn, addr = server_socket.accept()
    t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
    t.start()
