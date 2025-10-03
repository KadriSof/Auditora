# Auditora

[![PyPI version](https://badge.fury.io/py/levelapp.svg)](https://badge.fury.io/py/levelapp)  
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)  
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)

## Overview
A lightweight non-invasive instrumentation framework for data processing pipelines 
and LLM-powered systems.<br/> Auditora provides **session**, **monitor**, and **report** context objects
to track and surveil different events under **sentinel** watch.

## Context
Auditora leverages Python's **Context Variables** (introduced in Python 3.7) to provide 
execution-context-local storage that ensures complete isolation across threads, 
async coroutines, and nested contexts. Unlike traditional thread-local storage, 
Auditora's context management works seamlessly with both synchronous and asynchronous code, 
making it ideal for modern LLM applications and data processing pipelines.

## Features

- **Paragon**: Context variable storage manager with proper token-based context stack management
- **Adats**: Pluggable session, monitor, and report components with LLM-specific utilities
- **Bifrost**: Dual sync/async context managers for clean setup and teardown
- **Sentinel**: Intelligent decorator that automatically detects sync/async functions
- **Seamless Integration**: Use global `session`, `monitor`, `report` objects without parameters
- **LLM-Optimized**: Built-in support for LLM API calls, evaluation metrics, and multi-agent systems
- **Nested Context Support**: Proper context stack management enables complex evaluation scenarios
- **Thread & Async Safe**: Works correctly in multi-threaded and async/await environments

## Architecture

- **Paragon** (The Guardian): Context variable storage manager that maintains isolated execution contexts using Python's `contextvars`
- **Adats** (The Weavers): Pluggable components for state management (`Session`), performance monitoring (`Monitor`), and structured reporting (`Report`)
- **Bifrost** (The Bridge): Dual sync/async context managers that provide clean context boundaries with proper token-based restoration
- **Sentinel** (The Watcher): Intelligent decorator that automatically wraps functions with appropriate context management based on sync/async detection

## Installation

```bash
  pip install auditora
```

## Quick Start
### Basic Usage
```Python
from auditora import sentinel, session, monitor, report

@sentinel()
def evaluate_llm_response(response: str):
    report.info("Starting evaluation")
    session.set('response', response)
    
    # Simulate evaluation
    score = len(response) / 100.0
    monitor.increment_metric("coherence_score", score)
    report.log_evaluation_result("coherence", score, threshold=0.5)
    
    return score

# Usage
result = evaluate_llm_response("This is a sample LLM response.")
print(f"Session ID: {evaluate_llm_response._session.session_id}")
```

### Async Support
```Python
import asyncio
from auditora import sentinel, session, monitor, report

@sentinel()
async def async_llm_evaluation(query: str):
    report.info(f"Processing async query: {query}")
    
    # Simulate async LLM call
    await asyncio.sleep(0.1)
    
    session.set('query', query)
    monitor.track('async_processing_completed', query=query)
    report.log_llm_call(
        model="gpt-4",
        prompt_tokens=len(query.split()),
        completion_tokens=50,
        response_time=0.15
    )
    
    return {"status": "completed", "query": query}

# Run async function
asyncio.run(async_llm_evaluation("What is the meaning of life?"))
```

### Nested Context
```Python
from auditora import sentinel, bifrost_sync, session, monitor, report


@sentinel(session_id="inner_eval")
def inner_evaluation():
    session.set('inner_data', 'sub_evaluation')
    report.info("Inner evaluation running")

@sentinel(session_id="outer_eval")
def outer_evaluation():
    session.set('outer_data', 'main_evaluation')
    
    # Nested sub-evaluation call with its proper context management
    inner_evaluation()
    
    # Context automatically restored to outer evaluation
    report.info(f"Back to outer context: {session.get('outer_data')}")
```

## Advanced Configuration
```Python
from auditora.adata.session import DefaultSession

class CustomSession(DefaultSession):
    def __init__(self, session_id: str = None):
        super().__init__(session_id)
        self.custom_counter = 0
    
    def increment_counter(self):
        self.custom_counter += 1

@sentinel(session=CustomSession("custom_session"))
def custom_evaluation():
    session.increment_counter()
    report.info(f"Counter: {session.custom_counter}")
```

### Session ID Management
```Python
@sentinel(session_id="my_unique_session_123")
def tracked_evaluation():
    report.info(f"Running in session: {session.session_id}")
```

## Design Philosophy
Auditora follows the principle of non-invasive observability:

- **Zero parameter pollution**: Functions don't need context parameters
- **Automatic context management**: No manual setup/teardown required
- **Transparent integration**: Existing code works with minimal changes
- **Runtime safety**: Clear error messages when used incorrectly
- **Performance conscious**: Minimal overhead for monitoring operations

## Requirements
- Python 3.7+
- No external dependencies

## Use Cases
- **LLM Evaluation Pipelines**: Track metrics, log API calls, manage evaluation state
- **Multi-Agent Systems**: Monitor agent interactions and coordination
- **Data Processing Workflows**: Trace pipeline stages and performance metrics
- **API Monitoring**: Log structured metrics for LLM-powered endpoints
- **Testing and Debugging**: Inspect context objects externally for validation

## Acknowledgments

- Powered by [Norma](https://norma.dev).

## License

This project is licensed under the MIT License - see the [LICENCE](LICENCE) file for details.