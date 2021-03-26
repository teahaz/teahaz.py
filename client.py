import threading
import requests
import time

class Client:
    def __init__(self):
        self._url             = None
        self._chatid          = None
        self._session         = requests.Session()
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
            self._response[_response_key] = resp

            if callback:
                callback(resp)

        if method == "POST":
            _method = self._session.post
        elif method == "GET":
            _method = self._session.get

        _response_key = int(time.time())
        _handler = threading.Thread(_do_request,args=(response_key,)+request_args,kwargs=request_kwargs)
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

    def add_connection(url,chatid):
        data = self._connection_data
        if url in data.keys():
            data[url].append(chatid)
        else:
            data[url] = [chatid]

    def set_chatroom(self,url,index):
        pass


    # POST
    def login(self):
        pass

    def send_message(self):
        pass
    
    def send_file(self):
        pass


    # GET
    ## might be done from main loop
    def _get_messages(self):
        pass

    def get_file(self):
        pass


    # events

if __name__ == "__main__":
    c = Client()
