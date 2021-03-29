import threading
import requests
import base64
import pickle
import time
import json
import sys
import os


def encrypt_message(a):
    return base64.b64encode(str(a).encode('utf-8')).decode('utf-8')

def encrypt_binary(a):
    return base64.b64encode(a).decode('utf-8')

def decrypt_message(a):
    return base64.b64decode(str(a).encode('utf-8')).decode('utf-8')

def decrypt_binary(a):
    return base64.b64decode(str(a).encode('utf-8'))

def sanitize_filename(a):
    allowed = string.ascii_letters + string.digits + '_-.'
    a = a.replace('..', '_')

    filename = ''
    for i in a:
        if i not in allowed:
            i = '_'
        filename += i

    return filename



class Client:
    def __init__(self):
        self._url             = None
        self._chatid          = None
        self._session         = requests.Session()
        self._base_data       = { "User-Agent": "teahaz.py-v0.0" }
        self._responses       = {}
        self._connection_data = {}

    def run(self):
        pass


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

        _response_key = int(time.time())
        _handler = threading.Thread(target=_do_request,args=(_response_key,)+request_args,kwargs=request_kwargs)
        _handler.start()

        if join:
            # return response value from responses
            _handler.join()
            return self._responses[_response_key]
        else:
            # return key to future response
            return _response_key


    # utils
    @staticmethod
    def dbg(*args,**kwargs):
        print(**args,**kwargs)

    def is_set(self,key):
        return key in self._responses.keys()

    def get_response(self,key):
        value = self._responses.get(key)
        if value is not None:
            del self._responses[key]

        return value

    def add_connection(url,chatid):
        data = self._connection_data
        if url in data.keys():
            data[url].append(chatid)
        else:
            data[url] = [chatid]

    def set_chatroom(self,url,index):
        pass


    # POST
    def login(self,username,password,callback=None,url=None,join=False):
        def _set_data(resp):
            if resp.status_code == 200:
                data = resp.json()
                self._base_data['username'] = username
                self._chatid = data['chatroom']
                self._chatname = data['name']
            
            if callable(callback):
                callback(resp)

        if url == None:
            url = self._url
        else:
            self._url = url

        url += '/login/'+self._chatid

        data = self._base_data.copy()
        data['username'] = username
        data['password'] = password

        return self._request('POST',url=url,json=data,callback=_set_data,join=join)

    def send_message(self,text,replyid=None,callback=None,join=False):
        data = self._base_data.copy()
        data['type'] = 'text'
        data['message'] = encrypt_message(text)
        data['replyId'] = replyid

        url = self._url+'/api/v0/message/'+self._chatid

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


        url = self._url+'/api/v0/file/'+self._chatid

        data = self._base_data.copy()
        data['type']     = 'file'
        data['replyId']  = replyid
        data['filename'] = sanitize_filename(os.path.split(path)[1])

        length = os.path.getsize(path)
        fileobj = open(path,'rb+')
        
        t = threading.Thread(target=_send_chunks,args=(fileobj,url,data,callback))
        t.start()

    def use_invite(self,inviteid,username,nickname,password,email=None,callback=None,join=False):
        def _set_data(resp):
            if resp.status_code == 200:
                data = resp.json()
                self._base_data['username'] = username
                self._chatid = data['chatroom']
                self._chatname = data['name']

            if callable(callback):
                callback(resp)

            return resp


        data = self._base_data.copy()
        data['inviteId'] = inviteid
        data['username'] = username
        data['nickname'] = nickname
        data['password'] = password
        data['email']    = email

        url = self._url+'/api/v0/invite/'+self._chatid

        return self._request('POST',url=url,json=data,callback=_set_data,join=join)
        
        
        


    # GET
    def get_messages(self,since,callback=None):
        def _decrypt_messages(resp):
            if resp.status_code == 200:
                messages = resp.json()
                for m in messages:
                    if m.get('type') == 'text':
                        try:
                            m['message'] = decrypt_message(m['message'])
                        except:
                            continue

            if callback:
                callback(resp)

            return messages

        data = self._base_data.copy()
        data['time'] = str(since)
        url = self._url+'/api/v0/message/'+self._chatid

        return self._request('GET',url=url,headers=data,callback=_decrypt_messages)

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

        url = self._url+'/api/v0/file/'+self._chatid

        t = threading.Thread(target=_build_file,args=(url,headers,callback))
        t.start()

    def get_invite(self,expire_time,uses):
        data = self._base_data.copy()
        data['expr-time'] = str(expire_time)
        data['uses']      = str(uses)

        url = self._url+'/api/v0/invite/'+self._chatid

        return self._request('GET',url=url,headers=data)


    # events
    def on_message(self,messages):
        pass

def write_file(name,param,data):
    with open(name,param) as f:
        f.write(data)


if __name__ == "__main__":
    # c = Client()
    with open('client.obj','rb') as f:
        c = pickle.load(f)
        # print(c._base_data)

    # c._chatid = "3bfb6118-8aff-11eb-b3d7-0242ac110002"
    # key = c.login('alma','1234567890',url='https://teahaz.co.uk',callback=l,join=True)
    # key = c.login('eper','1234567890',url='https://teahaz.co.uk',callback=l,join=True)

    while not c.is_set(key):
        time.sleep(0.1)

    # print(c.get_response(key).text)
    # print(c._base_data)
    # print(c._chatid)
    # print(c._chatname)

    with open('client.obj','wb') as f:
        pickle.dump(c,f)

