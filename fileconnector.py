import io
# import time
import traceback

# import requests
# import streamlink

# RECONNECT_OFFLINE_DELAY = 5
# RECONNECT_DC_DELAY = 1

# TWITCH_URL_TEMPLATE = 'https://www.twitch.tv/{}'
# TWITCH_ONLINE_ENDPOINT = 'https://api.twitch.tv/kraken/streams/{}?client_id=5j0r5b7qb7kro03fvka3o8kbq262wwm&callback=badge.drawStream'

# STREAM_QUALITY = 'best'

class FileConnector:
    def __init__(self, event_id, twitch_id):
        self.event_id = event_id

    def on_connecting(self):
        pass

    def on_connected(self):
        pass

    def on_disconnected(self):
        pass

    def on_data(self, data):
        pass

    def run(self):
        print('******** starting for event {}'.format(self.event_id))
        try:
            self.on_connecting()

            with open('../frc2019nhsnh_one.mp4', 'rb') as s:
                self.on_connected()

                try:
                    while True:
                        data = s.read(io.DEFAULT_BUFFER_SIZE)
                        if len(data) == 0:
                            break
                        self.on_data(data)
                        import time
                        # time.sleep(1)
                finally:
                    self.on_disconnected()
                    print('******** disconnected event {}'.format(self.event_id))
        except KeyboardInterrupt:
            raise
        except:
            traceback.print_exc()

        # time.sleep(RECONNECT_DC_DELAY)
