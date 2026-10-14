uv run python << 'EOF'
from app.agent import ProductionAgent

agent = ProductionAgent()

print('=== PRODUCTION AGENT - STANDALONE TEST ===')
print()

queries = [
    'What is LangGraph in one sentence?',
    'What is 2 + 2?',
    'Explain the difference between RAG and fine-tuning in 2 sentences.',
]

for query in queries:
    print(f'--- Query: {query} ---')
    result = agent.invoke(query)
    response = result['response']
    model_used = result['model_used']
    error = result['error']
    print(f'Response: {response}')
    print(f'Model used: {model_used}')
    print(f'Error: {error}')
    print()

print('=== DONE ===')
EOF