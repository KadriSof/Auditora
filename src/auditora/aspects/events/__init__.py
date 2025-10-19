import msgpack


def serialize_event(event_data):
    return msgpack.packb(event_data, use_bin_type=True)

def deserialize_event(event_bytes):
    return msgpack.unpackb(event_bytes, raw=False)