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

	try:
		conn.sendall(serialized)
	except (BrokenPipeError, ConnectionResetError, OSError) as e:
		print(f"Socket error: {e}")
		conn.close()
		return
	except Exception as e:
		print(f"Unexpected error: {e}")
		conn.close()
		return
	try:
		data = conn.recv(65536)
		if data == b'':
			print("Clean disconnect at login")
			conn.close()
			return

		transport = TTransport.TMemoryBuffer(data)
		protocol = TCompactProtocol.TCompactProtocol(transport)
		msg = ChatProtocol()
		msg.read(protocol)

		if msg.type == MessageType.LOGIN_REQUEST:
			if msg.loginRequest is None:
				print("Malformed LOGIN_REQUEST message")
				conn.close()
				return

			name = msg.loginRequest.username
			with lock:
				users[name] = conn
			connections_queue2.put((conn, name))
		else:
			print("Login request is not LOGIN_REQUEST")
			conn.close()
			return
	except (BrokenPipeError, ConnectionResetError, OSError) as e:
		print(f"Socket error: {e}")
		conn.close()
	except Exception as e:
		print(f"Unexpected error: {e}")
		conn.close()

def receive_messages_from_queue():
	while True:
		conn, name = connections_queue2.get()
		receive_thread = threading.Thread(target=receive_messages, args=(conn, name,))
		receive_thread.start()

def receive_messages(conn, name):
	while True:
		ready_to_read, _, _ = select.select([conn], [], []) # no timeout means blocking

		if conn in ready_to_read:
			try:
				data = conn.recv(65536)

				if data == b'':
					print(f"Client {name} is down.")
					with lock:
						del users[name]
					conn.close()
					break

				transport = TTransport.TMemoryBuffer(data)
				protocol = TCompactProtocol.TCompactProtocol(transport)
				msg = ChatProtocol()
				msg.read(protocol)

				if msg.type == MessageType.SHOW_USERS_REQUEST:
					if msg.showUsersRequest is None:
						print("Malformed SHOW_USER_REQUEST message")

					names = None
					with lock:
						names = list(users.keys())
					if names is None:
						print("Unable to get usernames with lock")
						continue
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
					sender = name
					message_queue.put((sender, recipient, message))
			except (BrokenPipeError, ConnectionResetError, OSError) as e:
				print(f"Socket error: {e}")
				with lock:
					if name in users:
						del users[name]
				conn.close()
				break
			except Exception as e:
				print(f"Unexpected error: {e}")
				conn.close()
				break
		else:
			("No message available.")

def send_message_from_queue():
	while True:
		sender, recipient, message = message_queue.get()
		send_thread = threading.Thread(target=send_message, args=(sender, recipient, message))
		send_thread.start()

def send_message(sender, recipient, message):
	conn = None
	return_to_sender = None
	with lock:
		if recipient not in users: # send error message to sender
			if sender in users:
				conn = users[sender]
				return_to_sender = True
			else:
				print(f"Recipient {recipient} and sender {sender} is not online")
				return
		else:			
			conn = users[recipient]
			return_to_sender = False

	transport = TTransport.TMemoryBuffer()
	protocol = TCompactProtocol.TCompactProtocol(transport)
	chat_protocol = None
	if return_to_sender:
		chat_protocol = ChatProtocol(MessageType.ERROR, errorMessage=ErrorMessage(f"{recipient} is not online"))
	else:
		chat_protocol = ChatProtocol(MessageType.RECEIVE_MESSAGE, receiveMessage=ReceiveMessage(sender, message))
	chat_protocol.write(protocol)
	serialized = transport.getvalue()

	try:
		conn.sendall(serialized)
	except (BrokenPipeError, ConnectionResetError, OSError) as e:
		print(f"Socket error: {e}")
		with lock:
			if return_to_sender:
				if sender in users:
					del users[sender]
			else:
				if recipient in users:
					del users[recipient]
	except Exception as e:
		print(f"Unexpected error: {e}")

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
