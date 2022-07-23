import time

from hibye import call_service, wait_for_service

if __name__ == "__main__":
    wait_for_service("example_service", timeout=5)
    print("Client: sending ping")
    response = call_service("example_service", "ping")
    print("Client: received", response)

    print("Client: sending pang")
    response = call_service("example_service", "pang")
    print("Client: received", response)
