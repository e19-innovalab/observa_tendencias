"""Assistant: answers questions with the observatory's data through read-only API tools.

tools.py runs the tools (the API endpoints in app.yaml -> assistant.tools, called in-process);
numbers.py checks that the answer's numbers come from the tool results; providers.py talks to the
model (local OpenAI-compatible server or Anthropic); service.py puts it together, applies the
limits and writes assistant_logs.
"""
