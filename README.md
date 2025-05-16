# Hermes

Hermes is a feed monitoring system that analyzes RSS/Atom feeds for important updates, particularly focusing on retirements, deprecations, and breaking changes in specified applications and APIs. It uses AI to analyze entries and provides notifications through Slack.

![Hermes](https://github.com/igorzi84/Hermes/blob/main/feed_summary.jpg?raw=true)

## Features

- **Feed Monitoring**: Monitors multiple RSS/Atom feeds for updates
- **AI Analysis**: Uses OpenAI's GPT-4 to analyze feed entries for important changes
- **Deadline Tracking**: Identifies and tracks deadlines for important changes
- **PDF Reports**: Generates detailed PDF reports of analyzed entries, sorted by deadline
- **Slack Integration**: Sends notifications to Slack with summaries and PDF reports
- **Redis Storage**: Stores processed entries and their analysis in Redis
- **Targeted Monitoring**: Focuses on breaking changes for specific applications and APIs
- **Fast Dependency Management**: Uses UV for quick dependency installation
- **Containerized**: Docker support for easy deployment
- **Task Automation**: Taskfile for common development tasks

## Prerequisites

- Python 3.13 or higher
- Redis Cloud account (recommended) or Redis server
- OpenAI API key
- Slack Bot Token (for notifications)
- Taskfile (for automation)
- Docker and Docker Compose (optional)

## Installation

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hermes.git
cd hermes
```

2. Install Taskfile:
```bash
# macOS
brew install go-task/tap/go-task

# Linux
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin

# Windows
scoop install task
```

3. Install dependencies and setup environment:
```bash
# Install UV and Python dependencies
task install

# Or install without UV (using pip)
task install:no-uv
```

4. Create a `.env` file in the project root with the following variables:
```env
OPENAI_API_KEY=your_openai_api_key
REDIS_HOST=your-redis-cloud-host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_cloud_password
DEFAULT_KEYWORDS=breaking,deprecation,change,update
RSS_FEEDS=https://aws.amazon.com/blogs/aws/feed/,https://other-feed-url.com/feed/
BREAKING_CHANGE_TARGETS=AWS Lambda,Python 3.12,Node.js 18
SLACK_BOT_TOKEN=your-slack-bot-token
SLACK_CHANNEL=your-channel-id
```

### Docker Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hermes.git
cd hermes
```

2. Create a `.env` file as described above

3. Build and run with Docker Compose:
```bash
task docker:up
```

To run in detached mode:
```bash
task docker:up:detached
```

To stop the containers:
```bash
task docker:down
```

> **⚠️ Important Note about Redis Data Persistence**
> 
> When running Redis in Docker, data is not persisted by default. This means that when you stop and remove the containers, all cached feed entries and analysis results will be lost. We recommend using Redis Cloud for persistent storage:
> 
> 1. **Redis Cloud (Recommended)**:
>    - Sign up for a free Redis Cloud account at [redis.io](https://redis.io/try-free/)
>    - Create a new database
>    - Get your connection details (host, port, password)
>    - Update your `.env` file with the Redis Cloud credentials:
>      ```env
>      REDIS_HOST=your-redis-cloud-host
>      REDIS_PORT=6379
>      REDIS_PASSWORD=your_redis_cloud_password
>      ```
> 
> 2. **Docker Volume (Alternative)**:
>    If you prefer to use local Redis, modify the `docker-compose.yml` to add a volume:
>    ```yaml
>    services:
>      redis:
>        volumes:
>          - redis_data:/data
>    
>    volumes:
>      redis_data:
>    ```

## Usage

### Available Tasks

The project uses Taskfile for automation. Here are the available tasks:

#### Development Tasks
```bash
task install          # Install dependencies using UV sync
task clean          # Clean up temporary files
task test           # Run tests
task lint           # Run linters
```

#### Docker Tasks
```bash
task docker:up          # Start containers
task docker:up:detached # Start containers in detached mode
task docker:down        # Stop containers
task docker:build       # Build containers
task docker:logs        # View container logs
```

#### Application Tasks
```bash
task run              # Run the application
task run:keywords     # Run with specific keywords
task run:feeds        # Run with custom feeds
task run:verbose      # Run with verbose logging
task run:list-feeds   # List configured feeds
task run:report       # Generate PDF report
```

### Command Line Examples

```bash
# Run with default configuration
task run

# Search for specific keywords
task run -- keyword1 keyword2 keyword3

# Use custom feeds
task run -- --feeds "https://feed1.com/feed/,https://feed2.com/feed/"

# Enable verbose logging
task run -- --verbose

# List configured feeds
task run -- --list-feeds

# Generate PDF report
task run:report
```

### Targeted Monitoring

Configure which applications and APIs to monitor for breaking changes by setting the `BREAKING_CHANGE_TARGETS` environment variable:
```bash
export BREAKING_CHANGE_TARGETS="AWS Lambda,Python 3.12,Node.js 18,React 19,PostgreSQL 16"
```

The system will specifically look for:
- Breaking changes in these applications/APIs
- Deprecation notices
- End-of-life announcements
- Major version updates
- Security-critical changes

## Output

### PDF Reports

Generated PDF reports include:
- Title and generation timestamp
- Table of entries sorted by deadline
- Columns for Title, Published Date, Analysis, and Link
- Entries without deadlines are listed at the end

### Slack Notifications

Slack notifications include:
- Summary of important entries
- PDF report attachment
- Links to original sources
- Deadline information
- Required actions

## Development


## License

This project is licensed under the MIT License - see the LICENSE file for details.
