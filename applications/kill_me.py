import signal
from time import sleep


def signals():
    for num in dir(signal):
        if num.startswith(
                'SIG'
        ) and '_' not in num and num is not 'SIGKILL' and num is not 'SIGSTOP':
            yield getattr(signal, num)


def signal_handler(sig, _stack):
    print('got signal {}'.format(sig))
    sleep(100)


for sig in signals():
    signal.signal(sig, signal_handler)

sleep(100)
