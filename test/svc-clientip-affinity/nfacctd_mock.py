import socket
import select
import threading

tcp_port = 179
udp_port = 2055

lock = threading.Lock()
addresses={}

def udp_listen():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", 2055))
    while True:
        data, address = s.recvfrom(1024)
        print(f"[UDP] RX flowlog {address}")
        with lock:
            if address[0] not in addresses:
                print(f"[UDP][ERROR] Client IP {address} doesn't have an active BGP session!")

def tcp_listen():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 179))
    s.listen(5)

    epoll = select.epoll()
    epoll.register(s.fileno(), select.EPOLLIN)

    clients = {}
    while True:
        # Wait for events
        events = epoll.poll()

        for fileno, event in events:
            # New connection
            if fileno == s.fileno():
                c, address = s.accept()
                print(f"[TCP] {address}")

                # Register the client socket for read events
                epoll.register(c.fileno(), select.EPOLLIN)

                # Add the client socket to the dictionary
                clients[c.fileno()] = c
                addresses[address[0]] = c

            # Data available to read
            elif (event & select.EPOLLIN) or (event & select.EPOLLERR):
                c = clients[fileno]
                data = c.recv(1024)

                if not data:
                    epoll.unregister(fileno)
                    print(f"[TCP] CLOSE {c.getpeername()}")
                    with lock:
                        del addresses[c.getpeername()[0]]
                    c.close()
                    del clients[fileno]

t1 = threading.Thread(target=tcp_listen)
t2 = threading.Thread(target=udp_listen)
t1.start()
t2.start()
t1.join()
t2.join()
