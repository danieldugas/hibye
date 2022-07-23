# TODO: longer requests / responses
# TODO: list available services
# TODO: wait for service to be available
import socket
import select
import json
from threading import Thread

class Host(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

class DefaultHost(Host):
    def __init__(self):
        super(DefaultHost, self).__init__("localhost", 9999)

class ServiceRequest(object):
    def __init__(self, what, channel, data):
        self.what = what # "call_service", "is_service_advertised", ""
        self.channel = channel
        self.data = data

    def from_string(string):
        dic = json.loads(string)
        return ServiceRequest(dic["what"], dic["channel"], dic["data"])
    
    def from_bytes(data_list):
        json_string = "".join([data.decode("utf-8") for data in data_list])
        return ServiceRequest.from_string(json_string)

    def to_string(self):
        dic = {"what": self.what, "channel": self.channel, "data": self.data}
        return json.dumps(dic)

    def to_bytes(self):
        return self.to_string().encode("utf-8")
        

class ServiceResponse(object):
    def __init__(self, status, channel, data):
        self.status = status # "success", "exception"
        self.channel = channel
        self.data = data

    def from_string(string):
        dic = json.loads(string)
        return ServiceResponse(dic["status"], dic["channel"], dic["data"])
    
    def from_bytes(data_list):
        json_string = "".join([data.decode("utf-8") for data in data_list])
        return ServiceResponse.from_string(json_string)

    def to_string(self):
        dic = {"status": self.status, "channel": self.channel, "data": self.data}
        return json.dumps(dic)

    def to_bytes(self):
        return self.to_string().encode("utf-8")


def wait_for_service(channel, host=DefaultHost(), timeout=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host.ip, host.port))
    return s

def call_service(channel, request, host=DefaultHost(), s=None):  
    TCP_IP = host.ip
    TCP_PORT = host.port

    BUFFER_SIZE = 1024

    service_request = ServiceRequest("call_service", channel, request)

    if s is None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((TCP_IP, TCP_PORT))
    s.send(service_request.to_bytes())
    data_list = [s.recv(BUFFER_SIZE)]
    # data_list = []
    # while True:
    #     data = s.recv(BUFFER_SIZE)
    #     if not data:
    #         break
    #     data_list.append(data)
    s.close()

    service_response = ServiceResponse.from_bytes(data_list)
    if service_response.status == "success":
        return service_response.data
    elif service_response.status == "exception":
        print("In ServiceServer callback: ", service_response.data)
    else:
        raise ValueError("unknown status {}".format(service_response.status))

class ServiceServer(Thread):
    def __init__(self, host=DefaultHost(), run_in_main_thread=False):
        Thread.__init__(self)
        self.ip = host.ip
        self.port = host.port
        self.channels = {}
        if run_in_main_thread:
            pass
        else:
            self.start()

    def advertise(self, name, callback):
        self.channels[name] = callback

    def run(self):
        TCP_IP = self.ip
        TCP_PORT = self.port
        BUFFER_SIZE = 1024  # Normally 1024

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((TCP_IP, TCP_PORT))
        server_socket.listen(10)

        print("Listening on "+TCP_IP+":"+str(TCP_PORT))
        read_sockets, write_sockets, error_sockets = select.select([server_socket], [], [])

        while True:
            print("Waiting for incoming connections...")
            for sock in read_sockets:
                print("Receiving connection")
                (conn, (ip,port)) = server_socket.accept()
                data_list = []
                while True:
                    data = conn.recv(BUFFER_SIZE)
                    if not data:
                        break
                    data_list.append(data)
                    if len(data_list) == 0:
                        print("ignoring empty message")
                        continue
                    request = ServiceRequest.from_bytes(data_list)
                    print("received request:", request.to_string())
                    if request.what == "call_service":
                        if request.channel in self.channels:
                            callback = self.channels[request.channel]
                            try:
                                response_data = callback(request.data)
                            except Exception as e:
                                response = ServiceResponse("exception", request.channel, e.__repr__())
                            else:
                                response = ServiceResponse("success", request.channel, response_data)
                    else:
                        raise NotImplementedError
                    print("sending response:", response.to_string())
                    conn.send(response.to_bytes())