# Setting Up the BPT Slack Bot

This guide will walk you through setting up the BPT Slack bot integration, which allows users to ask questions about trading sessions using the `/ask-bpt` slash command.

## Prerequisites

1. A Slack workspace where you have admin permissions
2. The BPT API running (either locally or deployed)

## Step 1: Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" and choose "From scratch"
3. Enter a name for your app (e.g., "BPT Meeting Assistant")
4. Select your workspace and click "Create App"

## Step 2: Configure App Features

### Setup Socket Mode

1. In the left sidebar, click on "Socket Mode"
2. Enable Socket Mode
3. Create an app-level token with the `connections:write` scope
4. Copy the token that starts with `xapp-` – you'll need it later as `SLACK_APP_TOKEN`

### Configure Bot Token Scopes

1. In the left sidebar, click on "OAuth & Permissions"
2. Scroll down to "Bot Token Scopes" and add the following:
   - `chat:write` (to send messages)
   - `chat:write.public` (to send messages in channels the bot isn't in)
   - `commands` (to create slash commands)

### Create Slash Commands

1. In the left sidebar, click on "Slash Commands"
2. Click "Create New Command"
3. Fill in the details:
   - Command: `/ask-bpt`
   - Description: "Ask a question about a trading session"
   - Usage hint: "[your question]"
   - Check "Escape channels, users, and links sent to your app"
4. Click "Save"
5. Repeat to create a second command:
   - Command: `/ask-bpt-help`
   - Description: "Get help using the BPT Meeting Assistant"
   - Leave other fields default
   - Click "Save"

## Step 3: Install the App to Your Workspace

1. In the left sidebar, click on "Install App"
2. Click "Install to Workspace"
3. Review the permissions and click "Allow"
4. Copy the "Bot User OAuth Token" that starts with `xoxb-` – you'll need it later as `SLACK_BOT_TOKEN`

## Step 4: Configure Environment Variables

Add the following to your `.env` file:

```
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_BOT_TOKEN=xoxb-your-bot-token
```

If you're using Docker, you can add these to your `docker-compose.yml` file in the environment section.

## Step 5: Test the Integration

1. Start the BPT API
2. Check the logs to verify that the Slack bot started successfully
3. In Slack, use the `/ask-bpt-help` command to verify that the bot is working
4. Try asking a question with `/ask-bpt What was discussed in the last meeting?`

## Troubleshooting

### Bot Not Responding to Commands

- Check the API logs for errors
- Verify that both token environment variables are set correctly
- Make sure Socket Mode is enabled in your Slack app
- Ensure the app has the necessary scopes

### Command Not Found

- Verify that you've created the slash commands correctly
- Reinstall the app to your workspace to ensure permissions are up to date

### API Connection Issues

- Check that the QA endpoint is correctly configured in the `SlackService` initialization
- Verify that the API is running and accessible from the Slack service

### Testing Locally

When testing locally, you may need to:

1. Run the BPT API on a public URL using a service like ngrok
2. Update the slash command URLs to your public endpoint
3. Consider disabling socket mode and using HTTP endpoints during development

## Next Steps

After verifying the basic functionality, you may want to:

1. Add more slash commands for different functions
2. Implement interactive components for better UX
3. Add more detailed help and documentation
4. Configure response caching to improve performance 