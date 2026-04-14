from src.agent.primary_agent import get_agent_executor
executor = get_agent_executor()
print(executor.invoke({'input': 'Hi'}))

