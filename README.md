### Project Setup

1. **Create and activate a virtual environment:**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate
```

2. **Install dependencies with Poetry:**

```bash
pip install poetry
poetry install
```

3. **Create environment variables:**

In the project root, create a `.env` file and populate it with the environment variable values provided in our hackathon Slack channel. 


4. **Create environment variables:**

Run 

```bash
python3 talk_to_agent.py
```

If the LLM returns a response, your setup is complete and you can begin contributing