# TODO: longer requests / responses
# TODO: list available services
# TODO: wait for service to be available
# TODO: several hosts with named addresses? 
import socket
import select
import json
import time
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
    time_waited = 0
    time_increment = 0.5
    while True:
        try:
            s.connect((host.ip, host.port))
            break
        except ConnectionRefusedError:
            pass
        time.sleep(time_increment)
        time_waited += time_increment
        if timeout is not None and time_waited >= timeout:
            print("Timeout waiting for service {}".format(host, channel))
            return None
    return s

def get_advertised_services(master=DefaultHost()):
    TCP_IP = master.ip
    TCP_PORT = master.port

    BUFFER_SIZE = 1024

    service_request = ServiceRequest("list_services", "", "")

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
        data_dict = json.loads(service_response.data)
        return data_dict["advertised_services"]
    else:
        raise ValueError("unknown status {}".format(service_response.status))


def call_service(channel, request, master=DefaultHost(), s=None):  
    TCP_IP = master.ip
    TCP_PORT = master.port

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
    def __init__(self, master=DefaultHost(), run_in_main_thread=False, verbose=False):
        Thread.__init__(self)
        self.channels = {}
        self.verbose = verbose
        self.find_or_become_master(master)
        if run_in_main_thread:
            print("ServiceServer: run_in_main_thread set to true. Please call .run() method from main thread to start listening.")
        else:
            self.start()

    def find_or_become_master(self, master):
        TCP_IP = master.ip
        TCP_PORT = master.port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((TCP_IP, TCP_PORT))
            self.is_master = True
            self.master = master
        except OSError:
            raise NotImplementedError
            advertised_services = get_advertised_services(master=master)
            if advertised_services is None:
                raise ValueError("ServiceServer: could not find or become master")
            if self.verbose:
                print("A master server already exists. Will continue as slave")
                self.is_master = False
                self.master = master
                self.own_host_info = Host.get_next(master)

    def get_own_address(self):
        if self.is_master:
            return self.master

    def advertise(self, name, callback):
        self.channels[name] = callback

    def run(self):
        TCP_IP = self.get_own_address().ip
        TCP_PORT = self.get_own_address().port
        BUFFER_SIZE = 1024  # Normally 1024

        # server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # server_socket.bind((TCP_IP, TCP_PORT))
        self.server_socket.listen(10)

        if self.verbose:
            print("Listening on "+TCP_IP+":"+str(TCP_PORT))
        read_sockets, write_sockets, error_sockets = select.select([self.server_socket], [], [])

        while True:
            if self.verbose:
                print("Waiting for incoming connections...")
            for sock in read_sockets:
                if self.verbose:
                    print("Receiving connection")
                (conn, (ip,port)) = self.server_socket.accept()
                if self.verbose:
                    print("Accepted connection from "+ip+":"+str(port))
                data_list = []
                while True:
                    data = conn.recv(BUFFER_SIZE)
                    if not data:
                        break
                    data_list.append(data)
                    if len(data_list) == 0:
                        if self.verbose:
                            print("ignoring empty message")
                        continue
                    request = ServiceRequest.from_bytes(data_list)
                    if self.verbose:
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
                    if self.verbose:
                        print("sending response:", response.to_string())
                    conn.send(response.to_bytes())