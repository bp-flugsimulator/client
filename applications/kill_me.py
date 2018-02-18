import signal
from time import sleep

def signals():
    for num in dir(signal):
        if num.startswith('SIG') and '_' not in num:
            yield getattr(signal, num)

def signal_handler(sig, _stack):
    print('got signal {}'.format(sig))

for sig in signals():
    signal.signal(sig, signal_handler)

sleep(10)