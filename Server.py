import socket
import json
import select
import time
import threading
from cryptography.fernet import Fernet

def load_key(key_file="face_key.key"):
    """Load the face-derived key."""
    try:
        with open(key_file) as f:
            return json.load(f)["key"].encode()
    except Exception as e:
        print(f"Key load failed: {e}\nPlease run face_auth.py first!")
        return None

class TimeoutChecker(threading.Thread):
    """Thread to monitor client inactivity and close connection if timeout exceeded."""
    def __init__(self, conn, timeout=60):  # 60 second timeout by default
        threading.Thread.__init__(self)
        self.conn = conn
        self.timeout = timeout
        self.last_activity = time.time()
        self.running = True
        self.daemon = True  # Thread will close when main program exits
        
    def update_activity(self):
        self.last_activity = time.time()
        
    def stop(self):
        self.running = False
        
    def run(self):
        while self.running:
            if time.time() - self.last_activity > self.timeout:
                print(f"Client inactive for {self.timeout} seconds. Closing connection.")
                try:
                    self.conn.close()
                except:
                    pass  # Connection might already be closed
                self.running = False
                break
            time.sleep(1)  # Check every second

def start_server(connection_timeout=120, inactivity_timeout=60):
    """
    Start server with timeouts:
    - connection_timeout: seconds to wait for a client connection
    - inactivity_timeout: seconds to wait for client activity before disconnecting
    """
    key = load_key()
    if not key:
        return
    
    cipher = Fernet(key)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Configure socket for timeout
        server.settimeout(connection_timeout)
        server.bind(("0.0.0.0", 1234))
        server.listen()
        print(f"Server started. Waiting for client... (timeout: {connection_timeout}s)")
        
        try:
            conn, addr = server.accept()
            print(f"Connected to client at {addr}")
            
            # Set socket to non-blocking for select() usage
            conn.setblocking(False)
            
            # Start timeout monitoring thread
            timeout_checker = TimeoutChecker(conn, inactivity_timeout)
            timeout_checker.start()
            
            try:
                while True:
                    # Use select to wait for data or timeout
                    ready = select.select([conn], [], [], 1)  # 1 second polling
                    
                    if ready[0]:  # If socket has data to read
                        encrypted_msg = conn.recv(1024)
                        timeout_checker.update_activity()  # Update last activity timestamp
                        
                        if not encrypted_msg:
                            print("Connection closed by client.")
                            break
                        
                        decrypted_msg = cipher.decrypt(encrypted_msg).decode()
                        print("Client:", decrypted_msg)
                        
                        # Get server response with timeout indication
                        print(f"Enter response (you have {inactivity_timeout} seconds):")
                        reply = input("You: ")
                        
                        if reply:
                            encrypted_reply = cipher.encrypt(reply.encode())
                            conn.sendall(encrypted_reply)
                            timeout_checker.update_activity()
                    
                    # Check if timeout thread has terminated the connection
                    if not timeout_checker.running:
                        print("Connection closed due to timeout.")
                        break
                        
            except Exception as e:
                print(f"Error communicating with client: {e}")
            finally:
                timeout_checker.stop()
                conn.close()
                print("Client connection closed.")
        except socket.timeout:
            print(f"No client connected within {connection_timeout} seconds. Server shutting down.")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server.close()
        print("Server shutdown.")

if __name__ == "__main__":
    # You can adjust these timeouts as needed
    connection_timeout = 120  # Wait 2 minutes for initial client connection
    inactivity_timeout = 60   # Close connection after 1 minute of inactivity
    
    start_server(connection_timeout, inactivity_timeout)