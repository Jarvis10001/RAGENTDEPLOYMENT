"""End-to-end test with specific query that won't trigger clarification."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from api.session_manager import session_manager
from src.agent.primary_agent import stream_with_classifier

executor = session_manager.get_or_create('e2e-test-2')

collected_tool_outputs = []
final_output = None

# Use a very specific query that won't trigger clarification
query = 'Show me a bar chart of the top 5 marketing campaigns ranked by total revenue'

for msg in stream_with_classifier(executor, query):
    msg_type = msg.get("type")
    print(f"MSG type={msg_type}")
    
    if msg_type == "clarification":
        print(f"  CLARIFICATION: {msg.get('output', '')[:200]}")
    
    elif msg_type == "stream_chunk":
        chunk = msg.get("chunk", {})
        if "actions" in chunk:
            for action in chunk["actions"]:
                tool_name = getattr(action, "tool", "unknown")
                print(f"  TOOL_START: {tool_name}")
        
        elif "steps" in chunk:
            for step in chunk["steps"]:
                if hasattr(step, "action") and hasattr(step, "observation"):
                    action = step.action
                    observation = step.observation
                elif isinstance(step, (tuple, list)) and len(step) >= 2:
                    action, observation = step[0], step[1]
                else:
                    continue
                tool_name = getattr(action, "tool", "unknown")
                print(f"  TOOL_END: {tool_name} (output len={len(str(observation))})")
                collected_tool_outputs.append({
                    "tool": tool_name,
                    "output": str(observation)[:2000],
                })
        
        elif "output" in chunk:
            final_output = chunk["output"]
            print(f"  FINAL_OUTPUT received")

print(f"\n=== RESULT ===")
print(f"Collected {len(collected_tool_outputs)} tool outputs")

if collected_tool_outputs:
    from src.agent.visualization_agent import generate_chart_spec
    spec = generate_chart_spec(collected_tool_outputs)
    if spec:
        print(f"CHART GENERATED: type={spec['chart_type']} title={spec['title']} data_points={len(spec['data'])}")
    else:
        print("CHART SPEC: None (NO_CHART)")
else:
    print("NO TOOL OUTPUTS COLLECTED!")
