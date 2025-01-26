# Event Trigger Platform

Built using FastAPI for the API, Memcached for caching, and SQLite for the database.

## Deployment
Deployed on Oracle Free Tier: [Live Application](https://uwggw4c8408ckwgkc004cw04.host.saicharang.in)  
For API documentation: [Swagger Docs](https://uwggw4c8408ckwgkc004cw04.host.saicharang.in/docs)

---

## Local Setup Instructions

### Using Docker
```bash
docker run -p 8000:8000 ghcr.io/sai80082/segwise
```

### Without Docker

1. **Clone the Repository**
   ```bash
   git clone https://github.com/sai80082/segwise.git
   cd segwise
   ```

2. **Install Dependencies and Run the Application**
   Ensure Docker is installed on your machine.
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   fastapi dev app
   ```

3. **Access the Application**
   - Open your browser and navigate to [http://localhost:8000](http://localhost:8000).
   - To access the Swagger UI, go to [http://localhost:8000/docs](http://localhost:8000/docs).

4. **Environment Variables**
   Configure the following environment variables for testing the API trigger:
   - `HTTP_URL`: Discord webhook URL.

---

## Testing the application

You can run the tests for triggers using the following command:
```bash
PYTHONPATH=$(pwd) pytest tests/trigger_Test.py
```

---
## API Documentation

### Trigger Management

#### 1. **Create Trigger**
- **Endpoint**: `POST /triggers`  
- **Description**: Creates a new trigger with the specified configuration.  

**Request Payload**:
```json
{
  "name": "trigger1",
  "trigger_type": "scheduled",
  "schedule": "2026-01-26T08:43:51.801Z",
  "is_recurring": false,
  "interval_seconds": 0
}
```

**Request Example**:
```bash
curl -X 'POST' \
  'https://uwggw4c8408ckwgkc004cw04.host.saicharang.in/triggers/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "trigger1",
    "trigger_type": "scheduled",
    "schedule": "2026-01-26T08:43:51.801Z",
    "is_recurring": false,
    "interval_seconds": 0
  }'
```

**Response**:
```json
{
  "name": "trigger1",
  "trigger_type": "scheduled",
  "payload": "{}",
  "schedule": "2026-01-26T08:43:51.801000",
  "is_recurring": false,
  "interval_seconds": 0,
  "id": 1
}
```

---

#### 2. **Edit Trigger**
- **Endpoint**: `PUT /triggers/{id}`  
- **Description**: Updates an existing trigger by its ID.  

**Request Payload**:
```json
{
  "name": "updated_trigger",
  "trigger_type": "scheduled",
  "schedule": "2026-02-01T10:00:00.000Z",
  "is_recurring": true,
  "interval_seconds": 3600
}
```

**Request Example**:
```bash
curl -X 'PUT' \
  'https://uwggw4c8408ckwgkc004cw04.host.saicharang.in/triggers/{id}' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "updated_trigger",
    "trigger_type": "scheduled",
    "schedule": "2026-02-01T10:00:00.000Z",
    "is_recurring": true,
    "interval_seconds": 3600
  }'
```

---

#### 3. **Delete Trigger**
- **Endpoint**: `DELETE /triggers/{id}`  
- **Description**: Deletes a trigger by its ID.  

**Request Example**:
```bash
curl -X 'DELETE' \
  'https://uwggw4c8408ckwgkc004cw04.host.saicharang.in/triggers/{id}' \
  -H 'accept: application/json'
```

**Response**:
```json
{
  "detail": "Trigger deleted successfully from scheduler and database"
}
```

---

#### 4. **List Triggers**
- **Endpoint**: `GET /triggers`  
- **Description**: Retrieves a list of all triggers.  

**Request Example**:
```bash
curl -X 'GET' \
  'https://uwggw4c8408ckwgkc004cw04.host.saicharang.in/triggers/' \
  -H 'accept: application/json'
```

**Response**:
```json
[
  {
    "name": "trigger1",
    "trigger_type": "scheduled",
    "payload": "{}",
    "schedule": "2026-01-26T08:43:51.801000",
    "is_recurring": false,
    "interval_seconds": 0,
    "id": 1
  }
]
```

---

### Event Logs

#### 1. **Fetch Active Logs**
- **Endpoint**: `GET /logs/active`  
- **Description**: Retrieves the active event logs.  

**Request Example**:
```bash
curl -X 'GET' \
  'https://uwggw4c8408ckwgkc004cw04.host.saicharang.in/logs/active' \
  -H 'accept: application/json'
```

**Response**:
```json
[
  {
    "id": 29,
    "trigger_id": 2,
    "name": "Test1",
    "trigger_type": "scheduled",
    "triggered_at": "2025-01-26T08:51:20.723196",
    "payload": "{}",
    "is_test": false
  },
  {
    "id": 30,
    "trigger_id": 2,
    "name": "Test1",
    "trigger_type": "scheduled",
    "triggered_at": "2025-01-26T08:51:22.723010",
    "payload": "{}",
    "is_test": false
  }
]
```

---

#### 2. **Fetch Archived Logs**
- **Endpoint**: `GET /logs/archived`  
- **Description**: Retrieves archived event logs.  

**Request Example**:
```bash
curl -X 'GET' \
  'https://uwggw4c8408ckwgkc004cw04.host.saicharang.in/logs/archived' \
  -H 'accept: application/json'
```

**Response**:
```json
[
  {
    "id": 29,
    "trigger_id": 2,
    "name": "Test1",
    "trigger_type": "scheduled",
    "triggered_at": "2025-01-26T08:51:20.723196",
    "payload": "{}",
    "is_test": false
  },
  {
    "id": 30,
    "trigger_id": 2,
    "name": "Test1",
    "trigger_type": "scheduled",
    "triggered_at": "2025-01-26T08:51:22.723010",
    "payload": "{}",
    "is_test": false
  }
]
```

---

### Manual Testing

#### **Test Trigger**
- **Endpoint**: `POST /triggers/test`  
- **Description**: Manually triggers a test to simulate an event with a specified payload.  

**Request Payload**:
```json
{
  "name": "trigger1",
  "trigger_type": "scheduled",
  "schedule": "2026-01-26T08:43:51.801Z",
  "is_recurring": false,
  "interval_seconds": 0
}
```

**Request Example**:
```bash
curl -X 'POST' \
  'https://uwggw4c8408ckwgkc004cw04.host.saicharang.in/triggers/test/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "trigger1",
    "trigger_type": "scheduled",
    "schedule": "2026-01-26T08:43:51.801Z",
    "is_recurring": false,
    "interval_seconds": 0
  }'
```

**Response**:
```json
{
  "name": "trigger1",
  "trigger_type": "scheduled",
  "payload": null,
  "schedule": "2026-01-26T08:43:51.801000Z",
  "is_recurring": false,
  "interval_seconds": 0,
  "id": -70
}
```
## Assumption
 - I have assumed the api endpoint for testing the trigger as Discord webhook.you can set that using the env variable `HTTP_URL`.
 - The cache duration for statistics is set to 5 minutes to avoid frequent database queries, as fetching statistics for every trigger can be resource-intensive.

---

## Cost Estimation
For a reliable and cost effective hosting we can use a bare minimum of EC2 as we will get only 5 queris per day.
- **24/7 uptime** for 30 days.
- **5 queries per day**.
 - t4g.micro
 - 2 vcpus
 - 1 GiB RAM
 - Up to 5 Gigabit Network

The estimated cost is **$4.09/Month**, using the EC2 cost estimator.

**Credits**: Claude.ai,FastAPI docs,pypi docs.