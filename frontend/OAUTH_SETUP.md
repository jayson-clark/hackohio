# OAuth Setup Guide

This guide will help you set up Google OAuth authentication for the Synapse Mapper frontend.

## Prerequisites

1. A Google Cloud Platform account
2. Access to the Google Cloud Console

## Step 1: Create Google OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API (or Google Identity API)
4. Go to "Credentials" in the left sidebar
5. Click "Create Credentials" → "OAuth 2.0 Client IDs"
6. Choose "Web application" as the application type
7. Add your authorized JavaScript origins:
   - For development: `http://localhost:5173`
   - For production: your production domain
8. Copy the Client ID

## Step 2: Configure Environment Variables

Create a `.env` file in the frontend directory with the following content:

```env
# Google OAuth Configuration
VITE_GOOGLE_CLIENT_ID=your_google_client_id_here

# API Configuration (optional, defaults to http://localhost:8000)
VITE_API_URL=http://localhost:8000
```

Replace `your_google_client_id_here` with the Client ID you copied from Google Cloud Console.

## Step 3: Test the Setup

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Open your browser and navigate to `http://localhost:5173`
3. You should see a login screen with a "Continue with Google" button
4. Click the button to test the OAuth flow

## Features

- **Google OAuth Integration**: Secure authentication using Google accounts
- **Persistent Sessions**: User sessions are maintained across browser refreshes
- **Automatic Token Management**: Access tokens are automatically included in API requests
- **User Profile Display**: Shows user information and profile picture
- **Logout Functionality**: Secure logout with token cleanup

## Security Notes

- Access tokens are stored in localStorage (consider using httpOnly cookies for production)
- Tokens are automatically included in API requests
- 401 responses trigger automatic logout and token cleanup
- User data is stored locally and cleared on logout

## Troubleshooting

### "Configuration Error" Message
- Make sure you've set the `VITE_GOOGLE_CLIENT_ID` environment variable
- Restart the development server after adding the environment variable

### OAuth Popup Blocked
- Make sure your domain is added to the authorized JavaScript origins in Google Cloud Console
- Check that you're using HTTPS in production

### API Authentication Issues
- Verify that your backend is configured to accept Bearer tokens
- Check that the token is being sent in the Authorization header

## Backend Integration

The frontend sends the Google access token in the `Authorization` header as a Bearer token. Your backend should:

1. Verify the token with Google's token verification endpoint
2. Extract user information from the token
3. Create or update user records as needed
4. Use the user context for authorization decisions

Example backend token verification (Python/FastAPI):
```python
import httpx
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_google_token(token: str = Depends(security)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={token.credentials}"
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json()
```
