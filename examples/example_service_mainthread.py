import time

from hibye import ServiceServer

if __name__ == "__main__":
    service_server = ServiceServer(run_in_main_thread=True)
    def callback(request):
        if request == "ping":
            response = "pong"
        else:
            raise ValueError("unknown request {}".format(request))
        return response
    service_server.advertise("example_service", callback)
    service_server.run() # running in the mainthread
