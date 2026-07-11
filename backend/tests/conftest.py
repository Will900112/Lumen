"""Test environment setup.

Dummy credentials are assigned before any app module is imported, so
module-level API clients (OpenAI, Cohere, Pinecone) can be constructed
without real keys. Direct os.environ assignments take precedence over
backend/.env because load_dotenv() does not override existing variables.
"""

import os

os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789abcdef"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["COHERE_API_KEY"] = "test-cohere-key"
os.environ["PINECONE_API_KEY"] = "test-pinecone-key"
os.environ["LLAMA_CLOUD_API_KEY"] = "test-llama-key"
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
