import select
import socket
import sys
import threading
from thrift.protocol import TCompactProtocol
from thrift.transport import TTransport

sys.path.append('gen-py')

# Import generated classes
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

def connect_to_server():
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	host = socket.gethostname()
	port = 12354
	client_socket.connect((host, port))

	return client_socket

def login(client_socket):
	try:
		data = client_socket.recv(65536)
		transport = TTransport.TMemoryBuffer(data)
		protocol = TCompactProtocol.TCompactProtocol(transport)
		msg = ChatProtocol()
		msg.read(protocol)

		if msg.type == MessageType.LOGIN_RESPONSE:
			if msg.loginResponse is None:
				print("Malformed LOGIN_RESPONSE message")

			print(msg.loginResponse.prompt)  # What is your name?
			name = ""
			while not name:
				name = input()

			transport = TTransport.TMemoryBuffer()
			protocol = TCompactProtocol.TCompactProtocol(transport)
			login_request = ChatProtocol(MessageType.LOGIN_REQUEST, loginRequest=LoginRequest(name))
			login_request.write(protocol)
			serialized = transport.getvalue()

			client_socket.sendall(serialized)
		else:
			print("Login response is not LOGIN_RESPONSE")
	except (BrokenPipeError, ConnectionResetError, OSError) as e:
		print(f"Socket error: {e}")
	except Exception as e:
		print(f"Unexpected error: {e}")

def receive_messages():
	while True:
		ready_to_read, _, _ = select.select([client_socket], [], []) # no timeout means blocking

		if client_socket in ready_to_read:
			try:
				data = client_socket.recv(65536)
				if data == b'':
					print("Server is down")
					break

				transport = TTransport.TMemoryBuffer(data)
				protocol = TCompactProtocol.TCompactProtocol(transport)
				msg = ChatProtocol()
				msg.read(protocol)

				if msg.type == MessageType.SHOW_USERS_RESPONSE:
					if msg.showUsersResponse is None:
						print("Malformed SHOW_USERS_RESPONSE message")

					users = msg.showUsersResponse.users
					print("users: " + str(users))
				elif msg.type == MessageType.RECEIVE_MESSAGE:
					if msg.receiveMessage is None:
						print("Malformed RECEIVE_MESSAGE message")

					sender, message = msg.receiveMessage.sender, msg.receiveMessage.message
					print(f"{sender}: {message}")
				elif msg.type == MessageType.ERROR:
					if msg.errorMessage is None:
						print("Malformed ERROR message")
					error = msg.errorMessage.error
					print(error)
				else:
					print("Receive message is not RECEIVE_MESSAGE")
			except (BrokenPipeError, ConnectionResetError, OSError) as e:
				print(f"Socket error: {e}")
			except Exception as e:
				print(f"Unexpected error: {e}")
		else:
			("No message available.")

def get_message_attributes(message):
	split_by_spaces = message.split(" ")
	recipient, message = split_by_spaces[1], " ".join(split_by_spaces[2:])
	return recipient, message

def send_messages():
	while True:
		message = input()
		if message == "/show":
			transport = TTransport.TMemoryBuffer()
			protocol = TCompactProtocol.TCompactProtocol(transport)
			show_users_request = ChatProtocol(MessageType.SHOW_USERS_REQUEST, showUsersRequest=ShowUsersRequest())
			show_users_request.write(protocol)
			serialized = transport.getvalue()

			try:
				client_socket.sendall(serialized)
			except (BrokenPipeError, ConnectionResetError, OSError) as e:
				print(f"Socket error: {e}")
			except Exception as e:
				print(f"Unexpected error: {e}")
		elif message[:9] == "/message ":
			recipient, message = get_message_attributes(message)

			transport = TTransport.TMemoryBuffer()
			protocol = TCompactProtocol.TCompactProtocol(transport)
			send_message_request = ChatProtocol(MessageType.SEND_MESSAGE_REQUEST, sendMessageRequest=SendMessageRequest(recipient, message))
			send_message_request.write(protocol)
			serialized = transport.getvalue()

			try:
				client_socket.sendall(serialized)
			except (BrokenPipeError, ConnectionResetError, OSError) as e:
				print(f"Socket error: {e}")
			except Exception as e:
				print(f"Unexpected error: {e}")
		else:
			print("Invalid message. use /show or \'/message recipient message\'")

client_socket = None
while True:
	if not client_socket:
		line = input()
		if line == "start":
			client_socket = connect_to_server()
			login(client_socket)
	else:
		break

if client_socket:
	receive_thread = threading.Thread(target=receive_messages)
	receive_thread.start()

	send_thread = threading.Thread(target=send_messages)
	send_thread.start()
