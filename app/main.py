from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from forex_python.converter import CurrencyRates
from influxdb_client import InfluxDBClient
from enum import Enum
from dotenv import load_dotenv
import os

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
                        "lastUpdateTime": record.values.get("lastUpdateTime") if "lastUpdateTime" in record.values else None,
                        "time": str(record.get_time())
                    }
            if not found:
                print(f"No data found for symbol: {symbol}")  # Debug log
            return {"error": f"No data found for symbol: {symbol}"}
    except Exception as e:
        print(f"Error querying InfluxDB: {e}")  # Debug log
        return {"error": str(e)}


@app.get('/api/v1/lastprice/{symbol}')
def get_price_by_symbol(symbol: str):
    result = get_price(symbol)
    if "error" in result:
        return error_respone(result["error"])
    return success_respone(result)


@app.get('/api/v1/fiat/{symbol}')
def get_fiat_price_by_symbol(symbol: str):
    try:
        # Validate symbol using FIAT enum
        base = symbol[:3]
        quote = symbol[3:]
        result = get_price(base+quote)

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
        while True:
            result = get_price(symbol)

            # Broadcast the dummy data to all connected clients
            await manager.broadcast({
                "message": f"Broadcast from IP: {client_ip}",
                "data": result
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
