import msgpack
import statistics

from collections import deque


class DashboardConnector:
    def __init__(self, config):
        self.websocket_url = config.get('websocket_url')
        self.connected = False

    def connect(self):
        self.websocket = await websockets.connect(self.websocket_url)
        self.connected = True

    async def sent_update(self, data):
        if not self.connected:
            await self.websocket.send(msgpack.packb(data))


class MetricAggregator:
    def __init__(self, window_size=1000):
        self.window_size = window_size
        self.metrics_window = {}

    def add_metric(self, name, value):
        if name not in self.metrics_window:
            self.metrics_window[name] = deque(maxlen=self.window_size)
        self.metrics_window[name].append(value)

    def get_stats(self, name: str):
        window = self.metrics_window.get(name, None)
        if not window:
            return {}

        return {
            'count': len(window),
            'mean': statistics.mean(window)
            'median': statistics.median(window),
            'min': min(window),
            'max': max(window),
            'stdev': statistics.stdev(window) if len(window) > 1 else,
            'p95': statistics.quantiles(window, n=100)[94] if len(window) >= 20 else None,
        }