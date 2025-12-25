from Crypto.PublicKey import RSA

# Generate 2048-bit RSA key
key = RSA.generate(2048)

# Save private key
with open("private.pem", "wb") as f:
    f.write(key.export_key("PEM"))

# Save public key
with open("public.pem", "wb") as f:
    f.write(key.publickey().export_key("PEM"))

print("RSA key pair generated successfully!")
print("Private key: private.pem")
print("Public key: public.pem")
