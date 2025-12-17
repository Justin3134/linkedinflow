# LinkedIn Automation System

Complete LinkedIn automation system with AI-powered content generation and automated engagement.

## Project Structure

```
linkedin-automation/
├── frontend/              # React frontend (pro-pulse-studio)
│   └── src/
│       ├── pages/
│       └── components/
└── backend/               # Flask backend API
    ├── app.py            # Main Flask application
    ├── config.py         # Configuration
    ├── database.py       # Database models
    ├── services/         # Service modules
    │   ├── agiopen_client.py
    │   ├── openai_client.py
    │   └── image_generator.py
    └── requirements.txt
```

## Setup Instructions

### Backend Setup

1. Navigate to backend directory:
```bash
cd linkedin-automation/backend
```

2. Install dependencies (already done):
```bash
pip3 install -r requirements.txt
```

3. Set up environment variables (already configured):
The `.env` file is already created with your API keys.

4. Initialize database (already done):
```bash
python3 -c "from database import Base, engine; Base.metadata.create_all(engine)"
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd pro-pulse-studio
```

2. Install dependencies:
```bash
npm install
```

## Running the Application

### Start Backend Server

```bash
cd linkedin-automation/backend
python3 app.py
```

The backend will run on `http://localhost:5001`

### Start Frontend Server

In a new terminal:

```bash
cd pro-pulse-studio
npm run dev
```

The frontend will run on `http://localhost:8080`

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/read-source` - Read content from Apple Notes, Google Docs, or plain text
- `POST /api/generate-content` - Generate LinkedIn content (post/comment/message)
- `POST /api/create-post-draft` - Create LinkedIn post draft
- `POST /api/publish-post` - Publish the draft post
- `POST /api/get-post-comments` - Get comments on a post
- `POST /api/reply-to-comments` - Reply to comments
- `POST /api/message-likers` - Message people who liked a post
- `GET /api/history` - Get activity history

## Workflow

1. **Select Source**: Choose Apple Notes, Google Docs, or Plain Text
2. **Read Content**: Backend reads content from selected source using AGI Open API
3. **Choose Action**: Select Post, Comment, or Messages
4. **Generate Content**: OpenAI generates LinkedIn-optimized content
5. **Generate Image**: OpenAI DALL-E generates professional image (for posts)
6. **Review & Edit**: Review generated content in the UI
7. **Publish**: Create draft and publish on LinkedIn via AGI Open API
8. **Engage**: Optionally reply to comments or message likers

## Features

- ✅ Read from Apple Notes, Google Docs, or manual input
- ✅ AI-powered LinkedIn content generation
- ✅ Automatic image generation for posts
- ✅ LinkedIn automation via AGI Open API
- ✅ Comment reply automation
- ✅ Message automation for post likers
- ✅ Activity history tracking

## Notes

- Make sure both servers are running simultaneously
- The frontend communicates with the backend at `http://localhost:5001`
- All API keys are stored in `backend/.env`
- Database is stored in `backend/linkedin_automation.db`

