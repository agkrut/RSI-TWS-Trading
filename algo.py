import asyncio
import websockets
import json
import datetime
import dateutil.parser
import pprint

CoinbaseWSS = "wss://ws-feed.pro.coinbase.com"
SubMessage = {
    "type": "subscribe",
    "channels": [{"name": "ticker", "product_ids": ["BTC-USD"]}]
}
N = 14 # number of RSI periods
sticks = dict()

async def analyze(timestamp):
    MA1 = timestamp - datetime.timedelta(minutes=1) # one minute ago
    MA2 = timestamp - datetime.timedelta(minutes=2) # two minutes ago
    MA3 = timestamp - datetime.timedelta(minutes=3) # three minutes ago
    MA4 = timestamp - datetime.timedelta(minutes=4) # four minutes ago
    MA5 = timestamp - datetime.timedelta(minutes=5) # five minutes ago
    MA6 = timestamp - datetime.timedelta(minutes=6) # six minutes ago

    if MA6 in sticks:
        # detect bearish pattern
        if sticks[MA4]['close'] < sticks[MA5]['close'] < sticks[MA6]['close']:
            # detect bullish pattern
            if sticks[MA1]['close'] > sticks[MA2]['close'] > sticks[MA3]['close']:
                print("found three crows -> three white soldiers")

async def close(timestamp, price):
    # Previous minute / minute that just ended
    MA1 = timestamp - datetime.timedelta(minutes=1) # one minute ago
    MA2 = timestamp - datetime.timedelta(minutes=2) # two minutes ago
    MA14 = timestamp - datetime.timedelta(minutes=14) # fourteen minutes ago

    if MA1 in sticks and MA2 in sticks:
        # Sets close and change of previous minute
        sticks[MA1]['change'] = (sticks[MA1]['close'] / sticks[MA2]['close']) - 1

        # Need to get last 14 minutes [now-14,now-1]
        # We know the previous minute exists (i.e. now-1)
        # Second condition makes sure we start after first minute
        if MA14 in sticks and sticks[MA14]['change']:
            up = []
            down = []
            for i in range(N):
                minute = MA14 + datetime.timedelta(minutes=i)
                if sticks[minute]['change'] > 0: # positive change
                    up.append(sticks[minute]['change'])
                else:
                    down.append(sticks[minute]['change'])
            sticks[MA1]['rsi'] = 100 - 100 / (1 + sum(up) / sum(down))
            print("rsi: {}".format(sticks[MA1]['rsi']))

async def parse(payload):
    data = json.loads(payload)
    timestamp = dateutil.parser.parse(data['time']).replace(second=0, microsecond=0)
    price = float(data['price'])

    if timestamp not in sticks:
        await close(timestamp, price)
        await analyze(timestamp)
        sticks[timestamp] = {
            'open'   : price,
            'low'    : price,
            'high'   : price,
            'close'  : price,
            'change' : None,
            'rsi'    : None,
        }
    else:
        sticks[timestamp]['low'] = min(price, sticks[timestamp]['low'])
        sticks[timestamp]['high'] = max(price, sticks[timestamp]['high'])
        sticks[timestamp]['close'] = price

async def stream():
    async with websockets.connect(CoinbaseWSS) as ws:
        await ws.send(json.dumps(SubMessage)) # subscription send
        await ws.recv() # subscription confirm

        while True:
            try:
                payload = await ws.recv()
                await parse(payload)
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                break

def main():
    asyncio.get_event_loop().run_until_complete(stream())

if __name__ == "__main__":
    main()