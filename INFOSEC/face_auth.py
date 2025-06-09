import cv2
import face_recognition
import hashlib
import base64
import json
import os
import numpy as np

def capture_face(output_file="user_face.jpg"):
    """Capture face via webcam and save image."""
    cap = cv2.VideoCapture(0)
    print("Press 'S' to save your face, 'Q' to quit.")
    while True:
        ret, frame = cap.read()
        cv2.imshow("Face Registration", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            cv2.imwrite(output_file, frame)
            print(f"Face saved to {output_file}")
            break
        elif key == ord('q'):
            print("Exiting without save.")
            return None
    cap.release()
    cv2.destroyAllWindows()
    return output_file

def get_face_encoding(image_path):
    """Extract face encoding from image."""
    try:
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        if len(encodings) == 0:
            raise ValueError("No face detected")
        return encodings[0]
    except Exception as e:
        print(f"Face encoding failed: {e}")
        return None

def generate_key_from_string(seed_string):
    """Generate a Fernet-compatible key from any string."""
    # Create a consistent key from the string
    key_bytes = hashlib.sha256(seed_string.encode()).digest()
    # Convert to URL-safe base64 encoding for Fernet
    return base64.urlsafe_b64encode(key_bytes)

def save_user_data(face_encoding, key, data_file="face_data.json"):
    """Save both face encoding and derived key."""
    # Convert numpy array to list for JSON serialization
    encoding_list = face_encoding.tolist()
    
    # Create a static password as seed for the actual encryption key
    # This password never changes even if face recognition varies slightly
    password = "facial_auth_static_key_" + hashlib.md5(str(encoding_list).encode()).hexdigest()
    
    # Generate the actual encryption key from the password
    encryption_key = generate_key_from_string(password)
    
    data = {
        "face_encoding": encoding_list,
        "encryption_key": encryption_key.decode()
    }
    
    with open(data_file, 'w') as f:
        json.dump(data, f)
    print(f"User data saved to {data_file}")
    
    # Also save just the key in the original format for backward compatibility
    with open(key, 'w') as f:
        json.dump({"key": encryption_key.decode()}, f)
    print(f"Key saved to {key}")

def register_face():
    """Register a face and generate encryption key."""
    face_image = capture_face()
    if not face_image:
        return False
        
    face_encoding = get_face_encoding(face_image)
    if face_encoding is None:  # Fixed: proper way to check for None
        return False
        
    save_user_data(face_encoding, "face_key.key")
    print("Registration successful! You can now run server.py and client.py")
    return True

def verify_face(threshold=0.6):
    """Verify face against stored encoding using a threshold."""
    # Load stored face encoding
    try:
        with open("face_data.json") as f:
            data = json.load(f)
            stored_encoding = np.array(data["face_encoding"])
    except Exception as e:
        print(f"Cannot load stored face data: {e}")
        return False
    
    # Capture new face
    print("Please look at the camera for authentication...")
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    temp_image = "temp_face.jpg"
    cv2.imwrite(temp_image, frame)
    cap.release()
    
    # Get new face encoding
    new_encoding = get_face_encoding(temp_image)
    if new_encoding is None:  # Fixed: proper way to check for None
        print("No face detected in verification")
        return False
    
    # Compare with threshold
    # Lower distance means more similar faces
    face_distance = face_recognition.face_distance([stored_encoding], new_encoding)[0]
    
    print(f"Face similarity: {1 - face_distance:.2f}")
    result = face_distance <= threshold
    
    if result:
        print("Face verification successful!")
    else:
        print(f"Face verification failed (distance: {face_distance:.2f}, threshold: {threshold})")
    
    return result

if __name__ == "__main__":
    register_face()