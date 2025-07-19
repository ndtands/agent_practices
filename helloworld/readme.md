# Hello World Agent Demo

Đây là một demo đơn giản về việc triển khai một Agent sử dụng A2A SDK.

## Yêu cầu hệ thống
- Python 3.12 trở lên
- UV package manager

## Chi tiết các thành phần

### 1. Cấu trúc Agent (`agent_executor.py`)

```python
class HelloWorldAgent:
    async def ainvoke(self) -> str:
        return 'Hello World'
    
class HelloWorldAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = HelloWorldAgent()
```

Agent được định nghĩa với hai class chính:
- `HelloWorldAgent`: Class cơ bản với phương thức `ainvoke()` trả về "Hello World"
- `HelloWorldAgentExecutor`: Kế thừa từ `AgentExecutor` của a2a SDK, quản lý việc thực thi agent

### 2. Server Setup (`__main__.py`)

Server được cấu hình với các thành phần:

#### a. Định nghĩa Skills
```python
skill = AgentSkill(
    id='hello_world',
    name='Returns hello world',
    description='just returns hello world',
    tags=['hello world'],
    examples=['hi', 'hello world'],
)

extended_skill = AgentSkill(
    id='super_hello_world',
    name='Returns a SUPER Hello World',
    description='A more enthusiastic greeting',
    tags=['hello world', 'super', 'extended'],
)
```

#### b. Cấu hình Agent Card
```python
public_agent_card = AgentCard(
    name='Hello World Agent',
    description='Just a hello world agent',
    url=PUBLIC_URL,
    version='1.0.0',
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
    supportsAuthenticatedExtendedCard=True,
)
```

#### c. Khởi tạo Server
```python
server = A2AStarletteApplication(
    agent_card=public_agent_card,
    http_handler=request_handler,
    extended_agent_card=specific_extended_agent_card,
)
```

### 3. Client Implementation (`test_client.py`)

Client demo sử dụng a2a SDK để:
1. Kết nối với agent
2. Gửi tin nhắn
3. Nhận phản hồi (streaming và non-streaming)

#### Các bước chính:

```python
# 1. Khởi tạo Card Resolver
resolver = A2ACardResolver(
    httpx_client=httpx_client,
    base_url=base_url,
)

# 2. Lấy Agent Card
public_card = await resolver.get_agent_card()

# 3. Khởi tạo Client
client = A2AClient(
    httpx_client=httpx_client, 
    agent_card=final_agent_card_to_use
)

# 4. Gửi tin nhắn
response = await client.send_message(request)
```

## Hướng dẫn sử dụng A2A SDK

### 1. Tạo Agent mới

1. Định nghĩa Agent class với phương thức `ainvoke()`
2. Tạo AgentExecutor để quản lý agent
3. Định nghĩa skills của agent
4. Tạo AgentCard để mô tả agent
5. Khởi tạo server với A2AStarletteApplication

### 2. Tạo Client

1. Khởi tạo httpx client
2. Sử dụng A2ACardResolver để lấy thông tin agent
3. Khởi tạo A2AClient
4. Gửi tin nhắn và xử lý phản hồi

### 3. Authentication

Server hỗ trợ hai mode:
- Public: Không cần xác thực, chỉ có skill cơ bản
- Extended: Yêu cầu token xác thực, có thêm skill mở rộng

## Cài đặt và Chạy

### Phía Server

#### Cài đặt thư viện
Server cần các thư viện sau:
- a2a-sdk >= 0.2.12 (thư viện chính)
- uvicorn (cho web server)

#### Sử dụng UV

1. Cài đặt UV:
```bash
pip install uv
```

2. Cài đặt dependencies:
```bash
uv sync
```

3. Chạy server:
```bash
uv run .
```

Server sẽ chạy tại: http://localhost:9999

#### Sử dụng Docker

1. Build image:
```bash
docker build -t hello-world-agent .
```

2. Chạy container:
```bash
docker run -p 9999:9999 hello-world-agent
```

### Phía Client

1. Cài đặt thư viện:
```bash
uv sync
```

2. Chạy client demo:
```bash
uv run test_client.py
```

## Lưu ý

1. **Bảo mật**:
   - Token xác thực trong demo là "dummy-token-for-extended-card"
   - Trong production cần thay đổi token và cấu hình bảo mật phù hợp

2. **Streaming**:
   - Agent hỗ trợ cả streaming và non-streaming responses
   - Client demo minh họa cả hai cách gửi tin nhắn

3. **Error Handling**:
   - Client có xử lý lỗi khi không thể lấy extended card
   - Server có basic error handling cho các request không hợp lệ

**Flow của một request**:
1. Client gửi request đến server (localhost:9999)
2. Request được DefaultRequestHandler tiếp nhận
3. Request được chuyển đến HelloWorldAgentExecutor
4. Executor gọi HelloWorldAgent.invoke()
5. Kết quả "Hello World" được wrap trong text message
6. Message được đưa vào event queue
7. Response được trả về cho client

**Các điểm đáng chú ý**:
1. **Authentication**: Hỗ trợ 2 loại users (public và authenticated) với các skills khác nhau
2. **Streaming**: Agent có khả năng streaming (capabilities=AgentCapabilities(streaming=True))
3. **Task Management**: Sử dụng InMemoryTaskStore để quản lý tasks
4. **Async/Await**: Sử dụng async/await cho các operations bất đồng bộ
5. **Event Queue**: Sử dụng event queue để quản lý và trả về responses
6. **Error Handling**: Basic error handling với cancel operation

Đây là một ví dụ đơn giản nhưng đầy đủ các thành phần cơ bản của một A2A agent. Nó có thể được sử dụng làm template để xây dựng các agent phức tạp hơn.