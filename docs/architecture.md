# Hermes Project Architecture

## System Overview

```mermaid
graph TB
    subgraph "Feed Sources"
        RSS[RSS Feeds]
        AWS[AWS Blog]
        GCP[Google Cloud Blog]
        HashiCorp[HashiCorp Blog]
    end

    subgraph "Core Components"
        FP[FeedProcessor]
        AI[OpenAIWrapper]
        RC[RedisCache]
        SN[SlackNotifier]
        PDF[PDFGenerator]
    end

    subgraph "Output"
        Slack[Slack Channel]
        Reports[PDF Reports]
    end

    %% Feed Sources to FeedProcessor
    RSS --> FP
    AWS --> FP
    GCP --> FP
    HashiCorp --> FP

    %% FeedProcessor interactions
    FP --> AI
    FP --> RC
    FP --> SN
    FP --> PDF

    %% Output connections
    SN --> Slack
    PDF --> Reports

    %% Component details
    classDef component fill:#2c3e50,stroke:#34495e,stroke-width:2px,color:#ecf0f1
    classDef source fill:#34495e,stroke:#2c3e50,stroke-width:2px,color:#ecf0f1
    classDef output fill:#27ae60,stroke:#2c3e50,stroke-width:2px,color:#ecf0f1

    class FP,AI,RC,SN,PDF component
    class RSS,AWS,GCP,HashiCorp source
    class Slack,Reports output
```

## Component Details

### FeedProcessor
- Main orchestrator of the system
- Handles feed parsing and entry processing
- Manages the flow of data between components
- Implements keyword filtering and entry deduplication

### OpenAIWrapper
- Interfaces with OpenAI's API
- Analyzes feed entries for breaking changes
- Provides structured analysis in JSON format
- Handles rate limiting and retries

### RedisCache
- Stores processed entries
- Prevents duplicate processing
- Maintains entry history
- Enables quick lookups

### SlackNotifier
- Sends notifications to Slack
- Formats messages with important information
- Attaches PDF reports
- Handles error notifications

### PDFGenerator
- Creates detailed PDF reports
- Formats entry data for readability
- Includes analysis and deadlines
- Generates summary reports

## Data Flow

```mermaid
sequenceDiagram
    participant FP as FeedProcessor
    participant FParser as feedparser
    participant AI as OpenAIWrapper
    participant RC as RedisCache
    participant SN as SlackNotifier
    participant PDF as PDFGenerator
    

    FP->>FParser: Parse RSS Feeds
    FParser-->>FP: Feed Entries
    FP->>RC: Check for duplicates
    RC-->>FP: Entry status
    FP->>AI: Analyze entry
    AI-->>FP: Analysis result
    FP->>RC: Store entry
    FP->>SN: Send notification
    FP->>PDF: Generate report
    PDF-->>SN: Attach report
    SN->>SN: Send to Slack
```

## Configuration

The system is configured through environment variables:

- `OPENAI_API_KEY`: OpenAI API key
- `RSS_FEEDS`: Comma-separated list of feed URLs
- `DEFAULT_KEYWORDS`: Keywords to filter entries
- `BREAKING_CHANGE_TARGETS`: Tech stack components to monitor
- `REDIS_HOST`: Redis server hostname
- `REDIS_PORT`: Redis server port
- `REDIS_PASSWORD`: Redis server password
- `SLACK_BOT_TOKEN`: Slack bot token
- `SLACK_CHANNEL`: Target Slack channel

## Error Handling

```mermaid
graph TD
    A[Error Occurs] --> B{Error Type}
    B -->|Rate Limit| C[Wait & Retry]
    B -->|Invalid JSON| D[Return Error Response]
    B -->|Context Length| E[Truncate Content]
    B -->|Other| F[Log & Continue]
    
    C --> G[Max Retries?]
    G -->|Yes| H[Return Error Response]
    G -->|No| I[Retry Request]
    
    D --> J[Log Error]
    E --> K[Retry with Truncated Content]
    F --> L[Continue Processing]

    %% Error handling styling
    classDef error fill:#c0392b,stroke:#2c3e50,stroke-width:2px,color:#ecf0f1
    classDef decision fill:#2c3e50,stroke:#34495e,stroke-width:2px,color:#ecf0f1
    classDef action fill:#34495e,stroke:#2c3e50,stroke-width:2px,color:#ecf0f1

    class A,B error
    class G decision
    class C,D,E,F,H,I,J,K,L action
```

## Monitoring and Logging

The system uses Python's logging module with the following levels:
- DEBUG: Detailed information for debugging
- INFO: General operational information
- WARNING: Warning messages for potential issues
- ERROR: Error messages for failed operations

Each component logs its operations and errors, making it easy to track the system's behavior and diagnose issues. 