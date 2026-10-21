
services:
  - type: web
    name: dark-terminal-server
    runtime: python
    plan: starter
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: dark-terminal-db
          property: connectionString
      - key: PYTHON_VERSION
        value: 3.12.8

databases:
  - name: dark-terminal-db
    plan: basic-256mb
    databaseName: darkterminal
    user: darkterminal
