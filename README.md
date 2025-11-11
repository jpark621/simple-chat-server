# Simple Chat Server
Simple chat server with Thrift encoding

To generate thrift files, use

```
	thrift -r --gen py chat.thrift
```

## Times
| Session | Time |
| ------- | ---- |
| 1       | 2:04:57 |
| 2       | 2:03:58 |
| 3       | 1:58:39 |
| 4       | 2:14:24 |

## Claude Code Review

  - if there is a message in the message queue, but the recipient has been deleted, there will be a KeyError. I should check for the recipient when I send the message. \[FIXED\]
  - try-except around socket operations (recv and sendall) \[FIXED\]
  - recv() buffer size is too small \[FIXED\]
  - sockets should be .close() at exception \[FIXED\]