import socket
import json
import cv2
import time
import select
from cryptography.fernet import Fernet
from face_auth import verify_face

def load_key(key_file="face_key.key"):
    """Load the registered face key."""
    try:
        with open(key_file) as f:
            return json.load(f)["key"].encode()
    except Exception as e:
        print(f"No face key found: {e}. Run face_auth.py first!")
        return None

def start_client(auth_timeout=30, connection_timeout=10, response_timeout=60):
    """
    Start client with timeouts:
    - auth_timeout: seconds allowed for facial authentication
    - connection_timeout: seconds to wait when connecting to server
    - response_timeout: seconds to wait for server response
    """
    # Start auth timer
    auth_start_time = time.time()
    print(f"Authenticating with facial recognition... (timeout: {auth_timeout}s)")
    
    # Perform facial authentication with timeout
    if not verify_face():
        print("Authentication failed! Access denied.")
        return
    
    # Check if authentication took too long
    auth_duration = time.time() - auth_start_time
    if auth_duration > auth_timeout:
        print(f"Authentication took too long ({auth_duration:.1f}s > {auth_timeout}s timeout). Session expired.")
        return
    
    print(f"Authentication successful in {auth_duration:.1f}s! Connecting to server...")
    key = load_key()
    if not key:
        return
        
    cipher = Fernet(key)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Set connection timeout
        client.settimeout(connection_timeout)
        client.connect(("localhost", 1234))
        print("Connected to server. Start typing messages.")
        
        # Set to non-blocking for select() usage
        client.setblocking(False)
        
        while True:
            msg = input("You: ")
            if not msg:
                continue
                
            encrypted_msg = cipher.encrypt(msg.encode())
            client.sendall(encrypted_msg)
            
            # Wait for response with timeout
            print(f"Waiting for server response... (timeout: {response_timeout}s)")
            start_wait = time.time()
            
            while True:
                # Check for timeout
                if time.time() - start_wait > response_timeout:
                    print(f"Server didn't respond in {response_timeout} seconds. Connection timed out.")
                    client.close()
                    return
                
                # Use select to wait for data with a short timeout
                ready = select.select([client], [], [], 1)
                if ready[0]:  # If socket has data
                    try:
                        encrypted_reply = client.recv(1024)
                        if not encrypted_reply:
                            print("Connection closed by server.")
                            return
                            
                        decrypted_reply = cipher.decrypt(encrypted_reply).decode()
                        print("Server:", decrypted_reply)
                        break  # Exit the waiting loop, go back to input
                    except Exception as e:
                        print(f"Error receiving data: {e}")
                        return
    except socket.timeout:
        print(f"Could not connect to server within {connection_timeout} seconds.")
    except ConnectionRefusedError:
        print("Could not connect to server. Is the server running?")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        print("Connection closed.")

if __name__ == "__main__":
    # You can adjust these timeouts as needed
    auth_timeout = 30     # 30 seconds for facial authentication
    connect_timeout = 10  # 10 seconds to connect to server
    response_timeout = 60 # 60 seconds to wait for server response
    
    start_client(auth_timeout, connect_timeout, response_timeout)