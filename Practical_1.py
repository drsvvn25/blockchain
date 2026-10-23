
import hashlib

def encrypt(text, shift):
    result = ""

    for ch in text:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            result += chr(
                (ord(ch) - base + shift) % 26 + base
            )
        else:
            result += ch

    return result


def decrypt(text, shift):
    return encrypt(text, -shift)


message = "Hello Blockchain"
key = 3

encrypted = encrypt(message, key)
decrypted = decrypt(encrypted, key)

digest = hashlib.sha256(
    message.encode("utf-8")
).hexdigest()

print("Original:", message)
print("Encrypted:", encrypted)
print("Decrypted:", decrypted)
print("SHA-256:", digest)
