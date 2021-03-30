import os
import hashlib
import base64
from cryptography.fernet import Fernet

global TOKEN
TOKEN = ''

def _gen_token(a):
    "Generating token out of password, so It cannot be reversed"
    return base64.urlsafe_b64encode(str(hashlib.sha256(a.encode('utf-8')).digest())[:32].encode('utf-8'))


def _encrpt_string(string, token):
    "Encrypts a string given to it"
    f = Fernet(token)
    enc = f.encrypt(string.encode('utf-8'))
    return enc.decode('utf-8')


def _decrypt_string(encrypted_string, token):
    "Decrypts a string given to it"
    f = Fernet(token)
    dec = f.decrypt(encrypted_string.encode('utf-8'))
    return dec.decode('utf-8')



# get key from user
key = input('key: ')
# generate token
# no Idea why im using globals
globals()['TOKEN'] = _gen_token(key)
# overwrite key to destroy it in memory
key = os.urandom(256)


#some tests
enc = _encrpt_string("string", TOKEN)
print('enc: ',enc , type(enc))
dec = _decrypt_string(enc, TOKEN)
print('dec: ',dec , type(dec))
