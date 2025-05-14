# Hermes

Hermes is an intelligent RSS feed monitoring system that automatically detects and summarizes breaking changes and deprecations from various RSS feeds. It uses OpenAI's GPT-4 to analyze feed entries and provides concise summaries of important changes.

## Features

- 🔍 Monitors multiple RSS feeds concurrently
- 🤖 AI-powered analysis of feed entries
- 📝 Automatic summarization of breaking changes and deprecations
- 🔄 Deduplication of entries using content hashing
- 💾 Persistent storage of processed entries in Redis
- ⚡ Asynchronous processing for better performance
- 🛠️ Task automation with Taskfile
- 🐳 Docker support for easy deployment
- 🚀 UV for fast dependency management

## Prerequisites

- Python 3.13 or higher
- Redis Cloud account (recommended) or Redis server
- OpenAI API key
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
TECH_STACKS=Terraform,Boto3,API
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
```

## How It Works

1. **Feed Monitoring**: The system concurrently fetches multiple RSS feeds for new entries.

2. **Content Analysis**: Each entry is analyzed using OpenAI's GPT-4 to identify:
   - Breaking changes
   - Deprecations
   - Important updates
   - Deadlines for changes

3. **Deduplication**: Entries are hashed and stored in Redis to prevent duplicate processing.

4. **Storage**: Processed entries are stored in Redis with:
   - Original content
   - AI-generated summary
   - Metadata (title, link, publication date)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
