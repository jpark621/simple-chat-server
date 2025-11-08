namespace py chat

// Enums for message types
enum MessageType {
  LOGIN_REQUEST = 1,
  LOGIN_RESPONSE = 2,
  SHOW_USERS_REQUEST = 3,
  SHOW_USERS_RESPONSE = 4,
  SEND_MESSAGE_REQUEST = 5,
  RECEIVE_MESSAGE = 6,
  ERROR = 7,
  DISCONNECT = 8,
}

// Login messages
struct LoginRequest {
  1: required string username,
}

struct LoginResponse {
  1: required string prompt,  // "What is your name?"
}

// Show users messages
struct ShowUsersRequest {
  // Empty - just a request
}

struct ShowUsersResponse {
  1: required list<string> users,
}

// Chat messages
struct SendMessageRequest {
  1: required string recipient,
  2: required string message,
}

struct ReceiveMessage {
  1: required string sender,
  2: required string message,
}

// Error message
struct ErrorMessage {
  1: required string error,
}

// Disconnect message
struct DisconnectRequest {
  // Empty - just a signal
}

// Wrapper for all message types
struct ChatProtocol {
  1: required MessageType type,
  2: optional LoginRequest loginRequest,
  3: optional LoginResponse loginResponse,
  4: optional ShowUsersRequest showUsersRequest,
  5: optional ShowUsersResponse showUsersResponse,
  6: optional SendMessageRequest sendMessageRequest,
  7: optional ReceiveMessage receiveMessage,
  8: optional ErrorMessage errorMessage,
  9: optional DisconnectRequest disconnectRequest,
}
