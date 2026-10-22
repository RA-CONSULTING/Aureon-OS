from .ringbuffer import RingBuffer

class StreamHub:
    def __init__(self, streams: dict):
        self.streams = streams
        self.buffers = {name: RingBuffer(**config) for name, config in streams.items()}

    def push(self, stream_name, data):
        if stream_name in self.buffers:
            self.buffers[stream_name].push(data)

    def get_signals(self, last_n=None):
        return [buffer.read(last_n) for buffer in self.buffers.values()]
