# Evolyn Database Conversational Agent

A conversational AI agent that can interact with your Evolyn database to fetch account and facility information, save notes, and retrieve notes.

## 🚀 Quick Setup

### 1. Create Environment File
Create a `.env` file in the project root with your database credentials:

```env
OPENAI_API_KEY=your-openai-api-key-here
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=evolyn
DATABASE_USER=postgres
DATABASE_PASS=root
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Conversational Agent
```bash
python3 app.py
```

## 📁 Project Structure

```
/home/bitcot/supervisor/
├── app.py                 # Main conversational agent
├── database.py           # Database connection management
├── tools.py              # Database tools (fetch_account_details, fetch_facility_details, save_note, get_notes)
├── populate_database.py  # Database setup and population script
├── setup.sh              # Automated setup script
├── mock_data.json        # Sample data for database population
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables (create this)
```

## 🗄️ Database Schema

### Accounts Table
- `account_id` (Primary Key)
- `account_name`
- `status`
- `created_at`
- `pricing_model`
- Address fields
- Financial information (balance, points, etc.)
- Rewards and loyalty data

### Facilities Table
- `facility_id` (Primary Key)
- `facility_name`
- `status`
- `account_id` (Foreign Key)
- Medical license information
- Shipping address
- Agreement details

### Notes Table
- `note_id` (Primary Key)
- `account_id` (Foreign Key)
- `note_content`
- `created_at`
- `updated_at`
- `created_by`

## 🗣️ Usage Examples

Once the agent is running, you can ask questions like:

- "Show me account details for account_id A-011977763"
- "Find facilities for Dimod Account"
- "Save this note: Important meeting scheduled"
- "Show me notes for this account"
- "Show me all active facilities"
- "Find account by name 'Dimod'"

## 🌐 Web API

The agent can also be accessed via a REST API:

### Start Web API
```bash
python3 web_api.py
```

### API Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /chat` - Chat endpoint info
- `POST /chat` - Send messages to agent

### Example API Request
```bash
curl -X POST http://localhost:5050/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me account details for A-011977763",
    "account_id": "A-011977763"
  }'
```

## 🖥️ Terminal Mode

Run the agent directly in the terminal:

```bash
python3 local_run.py
```

## 🛠️ Troubleshooting

### Database Connection Issues
- Verify your PostgreSQL server is running
- Check database credentials in `.env` file
- Ensure the `evolyn` database exists

### OpenAI API Issues
- Verify your OpenAI API key is valid
- Check your API usage limits

### Permission Issues
- Make sure scripts are executable: `chmod +x *.sh`
- Check file permissions for database access