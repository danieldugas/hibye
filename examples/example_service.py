import time

from hibye import ServiceServer

if __name__ == "__main__":
    service_server = ServiceServer()
    def callback(request):
        if request == "ping":
            response = "pong"
        else:
            raise ValueError("unknown request {}".format(request))
        return response
    service_server.advertise("example_service", callback)

    while True:
        time.sleep(1.)
