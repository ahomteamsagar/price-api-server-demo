from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from forex_python.converter import CurrencyRates
from influxdb_client import InfluxDBClient
from enum import Enum
from dotenv import load_dotenv
import os,datetime

app = FastAPI()
c = CurrencyRates()
load_dotenv()

INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")


class TICKERS(Enum):
    BTCUSDC = 'BTCUSDC'
    BTCUSDT = 'BTCUSDT'
    BTCEUR = 'BTCEUR'
    ETHUSDT = 'ETHUSDT'
    ETHUSDC = 'ETHUSDT'
    ETHEUR = 'ETHEUR'
    USDTUSD = 'USDTUSD'
    USDCUSD = 'USDCUSD'


class FIAT(Enum):
    USD = 'USD'
    EUR = 'EUR'
    GBP = 'GBP'
    JPY = 'JPY'
    CHF = 'CHF'
    CNY = 'CNY'
    CAD = 'CAD'
    AUD = 'AUD'
    AED = 'AED'
crypto_map= {
    "btc":TICKERS.BTCUSDT.value,
    "eth":TICKERS.ETHUSDT.value
}
fiat_map= {
    "usd":FIAT.USD.value,
    "eur":FIAT.EUR.value,
    "gbp":FIAT.GBP.value,
    "jpy":FIAT.JPY.value,
    "chf":FIAT.CHF.value,
    "cny":FIAT.CNY.value,
    "cad":FIAT.CAD.value,
    "aud":FIAT.AUD.value,
    "aed":FIAT.AED.value
}

def success_respone(msg: any):
    return {
        'success': True,
        'message': msg
    }


def error_respone(error: any):
    return {
        'success': False,
        'error': error
    }


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: any):
        for con in self.active_connections:
            await con.send_json(data)


# connection manager
manager = ConnectionManager()


@app.get('/')
def welcome():
    return success_respone(msg="Price API server is running!")


def get_price(symbol: str):
    try:
        with InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
            query_api = client.query_api()
            query = f'''
                from(bucket: "{INFLUXDB_BUCKET}")
                  |> range(start: -24h)
                  |> filter(fn: (r) => r._measurement == "aggregated_price" and r.symbol == "{symbol}")
                  |> last()
            '''
            tables = query_api.query(query)

            found = False
            for table in tables:
                for record in table.records:
                    found = True
                    return {
                        "symbol": symbol,
                        "lastPrice": record.get_value(),
                        "time": str(datetime.datetime.now(tz=datetime.timezone.utc)),
                        "lastSnapshotTime":"10s"  # Placeholder for last update time
                    }
            if not found:
                print(f"No data found for symbol: {symbol}")  # Debug log
            return {"error": f"No data found for symbol: {symbol}"}
    except Exception as e:
        print(f"Error querying InfluxDB: {e}")  # Debug log
        return {"error": str(e)}


@app.get('/api/v1/lastprice/{symbol}')
def get_price_by_symbol(symbol: str):
    ticker = crypto_map.get(symbol.lower())
    result = get_price(ticker)
    if "error" in result:
        return error_respone(result["error"])
    return success_respone(result)


@app.get('/api/v1/crypto/fiat/{symbol}/{fiat}')
def get_fiat_price_by_symbol(symbol: str,fiat: str):
    try:
        ticker = crypto_map.get(symbol.lower())
        result = get_price(ticker)
        fiat_code = fiat_map.get(fiat.lower())
        rate = c.get_rate(FIAT.USD.value,fiat_code)  # Example conversion
        converted_price = result['lastPrice'] * rate if 'lastPrice' in result else 0
        result["lastPrice"] = converted_price
        result["currency"] = fiat
        if "error" in result:
            return error_respone(result["error"])
        return success_respone(result)

    except Exception as e:
        return error_respone(str(e))



@app.websocket('/ws')
async def websocket_router(websocket: WebSocket):
    client_ip = websocket.client.host  # Get client IP address
    await manager.connect(websocket)
    try:
        data = await websocket.receive_json()
        symbol = data.get('symbol', 'UNKNOWN')
        ticker= crypto_map.get(symbol.lower())  # Default to BTCUSDT if symbol not found
        while True:
            result = get_price(ticker)

            # Broadcast the dummy data to all connected clients
            await manager.broadcast({
                "message": f"Broadcast from IP: {client_ip}",
                "data": result
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
