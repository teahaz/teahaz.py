from cryptography.fernet import Fernet
from urllib.parse import urlparse
import threading
import requests
import hashlib
import string
import base64
import pickle
import time
import json
import sys
import os


# ENCRYPTION/DECRYPTION
def encrypt_message(a):
    return base64.b64encode(str(a).encode('utf-8')).decode('utf-8')

def encrypt_binary(a):
    return base64.b64encode(a).decode('utf-8')

def decrypt_message(a):
    return base64.b64decode(str(a).encode('utf-8')).decode('utf-8')

def decrypt_binary(a):
    return base64.b64decode(str(a).encode('utf-8'))

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


# HELPERS
def sanitize_filename(a):
    allowed = string.ascii_letters + string.digits + '_-.'
    a = a.replace('..', '_')

    filename = ''
    for i in a:
        if i not in allowed:
            i = '_'
        filename += i

    return filename

def get_and_del(key,d):
    value = d.get(key)
    if value is not None:
        del d[key]
    return value

def find_occurence(string,substring,num):
    start = 0
    index = 0
    for _ in range(num):
        index = string[start:].find(substring)
        if index == -1:
            break

        start += index+1
    return start

def interactive(function):
    import inspect
    assert callable(function)

    sig = inspect.signature(function)

    data = ()
    for i,(name,param) in enumerate(sig.parameters.items()):
        inp = input(name+': ')

        if inp.isdigit() and len(inp) == 1:
            inp = int(inp)
            data += (inp,)
        elif len(inp):
            data += (inp,)
        else:
            data += (param.default,)

    print('\n')
    print('calling\033[38;5;35m',function.__name__+'\033[m with\033[38;5;35m',data,'\033[m')

    ret = function(*data)
    print('return:',ret)

    return ret



class Client:
    def __init__(self):
        # internal data
        self._session         = requests.Session()
        self._base_data       = { "User-Agent": "teahaz.py-v0.0" }
        self._responses       = {}
        self._last_check      = '0'
        self._connection_data = {'servers': {}}

        # public data
        self.url              = None
        self.chatid           = None
        self.chatname         = None
        self.username         = None
        self.check_frequency  = 0.5

        # flags
        self._is_stopped      = False

    def run(self,url=None,chatid=None,username=None,password=None,frequency=None,hook_own_messages=False):
        if url is None:
            url = self.url

        if chatid is None:
            chatid = self.chatid

        if frequency is None:
            frequency = self.check_frequency

        assert url       is not None
        assert chatid    is not None
        assert frequency is not None

        if not self.is_connected(url):
            assert username is not None,"Not logged in to {url} and no username given."
            assert password is not None,"Not logged in to {url} and no password given."

            resp = self.login(username=username,password=password,url=url,chatid=chatid,join=True)
            if resp is not None:
                print(resp.json())
                return resp

        start = True
        self.username = self._base_data.get('username')

        self.on_ready()
        while not self._is_stopped:
            if not start:
                time.sleep(self.check_frequency)

            if self.is_paused():
                continue

            messages = self.get_messages(self._last_check,join=True)
            if not hook_own_messages:
                messages = [m for m in messages if not m.get('username') == self.username]

            if len(messages) and not start:
                threading.Thread(target=self.on_message,args=(messages,)).start()

            start = False
            time.sleep(self.check_frequency)


    # internal
    def _request(self, method, join=False, callback=None,*request_args,**request_kwargs):
        """
        Create and run a request using self._session.
        
        Arguments:
        <str> method:
            method to use in request.
            - allows: "POST"/"GET"

        <bool> join:
            boolean to decide if request Thread should be
            joined or not.
            - decides return value:
                * request.Response if join
                * else key into self._responses
                  NOTE: response should be del-d after use.
        """
        # TODO: maybe add conn_start & conn_end callbacks?
        def _do_request(_response_key,*args,**kwargs):
            resp = _method(*args,**kwargs)

            if callback:
                self._responses[_response_key] = callback(resp)
            else:
                self._responses[_response_key] = resp

        if method == "POST":
            _method = self._session.post
        elif method == "GET":
            _method = self._session.get
        elif method == "DELETE":
            _method = self._session.delete
        else:
            raise Exception('what is this method lol',str(method))

        _response_key = int(time.time())
        _handler = threading.Thread(target=_do_request,args=(_response_key,)+request_args,kwargs=request_kwargs)
        _handler.start()

        if join:
            # return response value from responses
            _handler.join()
            resp = self._responses[_response_key]
            del self._responses[_response_key]

            return resp
        else:
            # return key to future response
            return _response_key

    def _register(self,kwargs):
        def _set_data(resp):
            if resp.status_code == 200:
                data = resp.json()
                data['username'] = username
                self.add_connection(url,data)
            else:
                return resp

            if callable(callback):
                callback(resp)

        data = self._base_data.copy()

        # set up function params
        data['email']    = get_and_del('email',kwargs)
        callback         = get_and_del('callback',kwargs)
        join             = get_and_del('join',kwargs)
        url              = get_and_del('url',kwargs)
        username         = kwargs.get('username')

        # set up compulsory values
        data['username'] = username
        data['nickname'] = kwargs.get('nickname')
        data['password'] = kwargs.get('password')
        for key,value in kwargs.items():
            data[key] = value

        # assert not any(val is None for val in data.values())
        assert url is not None

        return self._request('POST',url=url,json=data,callback=_set_data,join=join)


    # utils
    def is_set(self,key):
        return key in self._responses.keys()

    def is_paused(self):
        return False

    def get_response(self,key):
        return get_and_del(key,self._responses)

    def get_chatroom(self,url,index):
        if not url.endswith('/'):
            url += '/'

        return self._connection_data['servers'][url][index]

    def add_connection(self,url,chatroom_dict,_set=True):
        data = self._connection_data['servers']

        url = url.strip('/')
        if url.count('/') > 2:
            end = find_occurence(url,'/',3)
            url = url[:end]

        if url in self._connection_data['servers'].keys():
            data[url].append(chatroom_dict)
        else:
            data[url] = [chatroom_dict]

        if _set:
            self.set_chatroom(url,chatroom_dict)

    def set_chatroom(self,url,chatroom_dict):
        data = self._connection_data

        assert url in data['servers'].keys()

        self.url                   = url
        self.chatid                = chatroom_dict.get('chatroom')
        self._chatname              = chatroom_dict.get('name')
        self._base_data['username'] = chatroom_dict.get('username')
        self.username               = self._base_data['username']

    def is_connected(self,url):
        for cookie in self._session.cookies:
            if cookie.domain == urlparse(url).netloc.split(':')[0]:
                return True
        else:
            return False

        
    # POST
    def login(self,username,password,callback=None,url=None,chatid=None,join=False):
        def _set_data(resp):
            if resp.status_code == 200:
                data = resp.json()
                self._base_data['username'] = username
                self.username  = username
                self.chatid    = data['chatroom']
                self.chatname = data['name']
            else:
                return resp
            
            if callable(callback):
                callback(resp)


        if url == None:
            url = self.url
        else:
            self.url = url

        if chatid == None:
            chatid = self.chatid
        else:
            self.chatid = chatid

        url += '/login/'+chatid

        data = self._base_data.copy()
        data['username'] = username
        data['password'] = password

        return self._request('POST',url=url,json=data,callback=_set_data,join=join)

    def send_message(self,text,replyid=None,callback=None,join=False):
        data = self._base_data.copy()
        data['type'] = 'text'
        data['message'] = encrypt_message(text)
        data['replyId'] = replyid

        url = self.url+'/api/v0/message/'+self.chatid

        return self._request('POST',url=url,json=data,callback=callback,join=join)

    def send_file(self,path,replyid=None,callback=None,join=False):
        def _send_chunks(fileobj,url,data,callback):
            chunk_size = int((1048576*3)/4) - 1
            content    = True
            fileId     = None

            while content:
                chunk = fileobj.read(chunk_size)

                if len(chunk) < chunk_size or f.tell() >= length:
                    content = False

                data['fileId'] = fileId
                data['part']   = content
                data['data']   = encrypt_binary(chunk)

                resp = self._request('POST',url=url,json=data,join=True)
                if not resp.status_code == 200:
                    break
                else:
                    fileId = resp.text.strip(' ').strip('\n').strip('"')

            fileobj.close()

            if callback:
                callback(resp)


        url = self.url+'/api/v0/file/'+self.chatid

        data = self._base_data.copy()
        data['type']     = 'file'
        data['replyId']  = replyid
        data['filename'] = sanitize_filename(os.path.split(path)[1])

        length = os.path.getsize(path)
        fileobj = open(path,'rb+')
        
        t = threading.Thread(target=_send_chunks,args=(fileobj,url,data,callback))
        t.start()

    # TODO: add assertions for chatid
    def use_invite(self,inviteId,username,nickname,password,url=None,chatid=None,email=None,callback=None,join=False):
        data = {}
        data['inviteId'] = inviteId
        data['username'] = username
        data['nickname'] = nickname
        data['password'] = password
        data['email']    = email
        data['join']     = join
        if url is None:
            url = self.url

        if chatid is None:
            chatid = self.chatid

        assert url is not None,'url is not set! add it to parameters of create_chatroom'
        data['url']      = url+'/api/v0/invite/'+chatid

        return self._register(data)
        
    def create_chatroom(self,chatroom_name,username,nickname,password,url=None,chatid=None,email=None,callback=None,join=False):
        data = {}
        data['chatroom_name'] = chatroom_name
        data['username']      = username
        data['nickname']      = nickname
        data['password']      = password
        data['email']         = email
        data['join']          = join
        if url is None:
            url = self.url

        if chatid is None:
            chatid = self.chatid

        assert url is not None,'url is not set! add it to parameters of create_chatroom'
        data['url']      = url+'/api/v0/chatroom/'

        return self._register(data)
        

    # GET
    def get_messages(self,since=None,callback=None,join=False):
        def _decrypt_messages(resp):
            if resp.status_code == 200:
                messages = resp.json()
                for m in messages:
                    if m.get('type') == 'text':
                        try:
                            m['message'] = decrypt_message(m['message'])
                        except:
                            continue
            else:
                return resp

            if callable(callback):
                ret = callback(messages)
                if ret:
                    return ret

            return messages

        if since is None:
            since = self._last_check
        self._last_check = str(time.time())

        data = self._base_data.copy()
        data['time'] = str(since)
        url = self.url+'/api/v0/message/'+self.chatid

        return self._request('GET',url=url,headers=data,callback=_decrypt_messages,join=join)

    def get_file(self,fileid,callback):
        def _build_file(url,headers,callback):
            section = 0
            data = b''
            while True:
                headers['section'] = str(section + 1)
                section += 1

                resp = self._request('GET',url=url,headers=headers,join=True)
                if resp.status_code == 200:
                    stripped = resp.json()
                    
                    if not len(stripped):
                        break
                    else:
                        try:
                            data += decrypt_binary(stripped)
                        except:
                            data = b'Corrupt'
                            break
                else:
                    break

            callback(data)

        headers = self._base_data.copy()
        headers['fileId'] = fileid

        url = self.url+'/api/v0/file/'+self.chatid

        t = threading.Thread(target=_build_file,args=(url,headers,callback))
        t.start()

    def get_invite(self,expire_time,uses,join=False):
        data = self._base_data.copy()
        data['expr-time'] = str(expire_time)
        data['uses']      = str(uses)

        url = self.url+'/api/v0/invite/'+self.chatid

        return self._request('GET',url=url,headers=data,join=join)
    
    def get_by_id(self,messageId,callback=None,join=False):
        def _decrypt_message(resp):
            if resp.status_code == 200:
                message = resp.json()[0]
                if message.get('type') == 'text':
                    message['message'] = decrypt_message(message['message'])
            else:
                return resp

            if callable(callback):
                callback(resp)

            return message


        data = self._base_data.copy()
        data['messageId'] = messageId

        url = self.url+'/api/v0/message/'+self.chatid

        return self._request('GET',url=url,headers=data,callback=_decrypt_message,join=join)


    # DELETE
    def delete_message(self,messageId,callback=None,join=False):
        data = self._base_data.copy()
        data['messageId'] = messageId

        url = self.url+'/api/v0/message/'+self.chatid

        return self._request('DELETE',url=url,json=data,callback=callback,join=join)


    # events
    def on_ready(self):
        self.send_message('beep-boop')

    def on_message(self,messages):
        print('new message!')

    def on_download(self,status):
        # TODO: future, not supported by server
        #      for now.
        return
