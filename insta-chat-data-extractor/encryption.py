from cryptography.fernet import Fernet
import os

# Generate a key once and save it securely (do not regenerate every run!)
# key = Fernet.generate_key()
# For demonstration, you can generate a key like this:
# Make sure to run this only once and save the key securely!
#print(Fernet.generate_key().decode())

# Save this key somewhere safe and load it for both encryption and decryption



def encrypt_messages(messages):
    FERNET_KEY = os.getenv("FERNET_KEY")  # Or load from a file
    fernet = Fernet(FERNET_KEY)
    # Join messages as a single string, then encrypt
    joined = "\n".join(messages)
    encrypted = fernet.encrypt(joined.encode("utf-8"))
    return encrypted.decode("utf-8")

def decrypt_messages(encrypted_text):
    FERNET_KEY = os.getenv("FERNET_KEY")  # Or load from a file
    fernet = Fernet(FERNET_KEY)
    decrypted = fernet.decrypt(encrypted_text.encode("utf-8"))
    return decrypted.decode("utf-8").split("\n")