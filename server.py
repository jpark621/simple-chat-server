from queue import Queue
import select
import socket
import sys
import threading
from thrift.protocol import TCompactProtocol
from thrift.transport import TTransport

sys.path.append('gen-py')

from chat.ttypes import (
	MessageType,
	LoginRequest,
	LoginResponse,
	ShowUsersRequest,
	ShowUsersResponse,
	SendMessageRequest,
	ReceiveMessage,
	ErrorMessage,
	ChatProtocol
)

def start_server():
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	host = socket.gethostname()
	port = 12354
	server_socket.bind((host, port))
	return server_socket

def listen():
	server_socket.listen()

	while True:
		conn, addr = server_socket.accept()
		print(f"Connection from {addr}")

		connections_queue.put(conn)

def login_from_queue():
	while True:
		conn = connections_queue.get()
		login_thread = threading.Thread(target=login, args=(conn,))
		login_thread.start()

def login(conn):
	transport = TTransport.TMemoryBuffer()
	protocol = TCompactProtocol.TCompactProtocol(transport)
	login_response = ChatProtocol(MessageType.LOGIN_RESPONSE, loginResponse=LoginResponse("What is your name?"))
	login_response.write(protocol)
	serialized = transport.getvalue()

	conn.sendall(serialized)
	data = conn.recv(1024)

	transport = TTransport.TMemoryBuffer(data)
	protocol = TCompactProtocol.TCompactProtocol(transport)
	msg = ChatProtocol()
	msg.read(protocol)

	if msg.type == MessageType.LOGIN_REQUEST:
		if msg.loginRequest is None:
			print("Malformed LOGIN_REQUEST message")

		name = msg.loginRequest.username
		with lock:
			users[name] = conn
		connections_queue2.put((conn, name))
	else:
		print("Login request is not LOGIN_REQUEST")

def receive_messages_from_queue():
	while True:
		conn, name = connections_queue2.get()
		receive_thread = threading.Thread(target=receive_messages, args=(conn, name,))
		receive_thread.start()

def receive_messages(conn, name):
	while True:
		ready_to_read, _, _ = select.select([conn], [], []) # no timeout means blocking

		if conn in ready_to_read:
			data = conn.recv(1024)

			if data == b'':
				with lock:
					del users[name]
				print(f"Client {name} is down.")
				break

			transport = TTransport.TMemoryBuffer(data)
			protocol = TCompactProtocol.TCompactProtocol(transport)
			msg = ChatProtocol()
			msg.read(protocol)

			if msg.type == MessageType.SHOW_USERS_REQUEST:
				if msg.showUsersRequest is None:
					print("Malformed SHOW_USER_REQUEST message")

				names = list(users.keys())
				show_users_response = ChatProtocol(MessageType.SHOW_USERS_RESPONSE, showUsersResponse=ShowUsersResponse(names))

				transport = TTransport.TMemoryBuffer()
				protocol = TCompactProtocol.TCompactProtocol(transport)
				show_users_response.write(protocol)
				serialized = transport.getvalue()

				conn.sendall(serialized)
			elif msg.type == MessageType.SEND_MESSAGE_REQUEST:
				if msg.sendMessageRequest is None:
					print("Malformed SEND_MESSAGE_REQUEST message")

				recipient, message = msg.sendMessageRequest.recipient, msg.sendMessageRequest.message
				if recipient not in users:
					transport = TTransport.TMemoryBuffer()
					protocol = TCompactProtocol.TCompactProtocol(transport)
					error_message = ChatProtocol(MessageType.ERROR, errorMessage=ErrorMessage(f"{recipient} is not online"))
					error_message.write(protocol)
					serialized = transport.getvalue()

					conn.sendall(serialized)
					continue
				sender = name
				message_queue.put((sender, recipient, message))
			
		else:
			("No message available.")

def send_message_from_queue():
	while True:
		sender, recipient, message = message_queue.get()
		send_thread = threading.Thread(target=send_message, args=(sender, recipient, message))
		send_thread.start()

def send_message(sender, recipient, message):
	conn = users[recipient]

	transport = TTransport.TMemoryBuffer()
	protocol = TCompactProtocol.TCompactProtocol(transport)
	receive_message = ChatProtocol(MessageType.RECEIVE_MESSAGE, receiveMessage=ReceiveMessage(sender, message))
	receive_message.write(protocol)
	serialized = transport.getvalue()

	conn.sendall(serialized)

server_socket = None
while True:
	if not server_socket:
		line = input()
		if line == "start":
			server_socket = start_server()
	else:
		break

if server_socket:
	connections_queue = Queue()
	listen_thread = threading.Thread(target=listen)
	listen_thread.start()

	users = {}
	lock = threading.Lock()
	connections_queue2 = Queue()
	login_from_queue_thread = threading.Thread(target=login_from_queue)
	login_from_queue_thread.start()

	message_queue = Queue()
	receive_from_queue_thread = threading.Thread(target=receive_messages_from_queue)
	receive_from_queue_thread.start()

	send_from_queue_thread = threading.Thread(target=send_message_from_queue)
	send_from_queue_thread.start()
