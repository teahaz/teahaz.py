from teahaz import Client,interactive
import time,pickle,os,requests


class Bot(Client):
    def __init__(self):
        super().__init__()

    def on_ready(self):
        print('ready!')

    def on_message(self,messages):
        for m in messages:
            self.send_message('I heard that!:robot:')
            print('new message')
    

# initial interactive setup
if __name__ == "__main__":
    if 'bot.obj' in os.listdir():
        with open('bot.obj','rb') as f:
            b = pickle.load(f)
        b.run()

    else:
        mode = input('login or invite? ')
        while mode not in ['login','invite']:
            print('invalid mode! choices:',['login','invite'])
            mode = input('login/invite')

        b = Bot()
        if mode == 'login':
            ret = interactive(b.login)
        else:
            ret = interactive(b.use_invite)


        print()
        if ret == None:        
            print('setup done! restart the bot.')
            with open('bot.obj','wb') as f:
                pickle.dump(b,f)

        else:
            print('something went wrong!')

            if isinstance(ret,requests.Response):
                print('response code:',ret.status_code)
                print('response text:',ret.text)

            print('restart to try again.')
