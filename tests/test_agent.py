import subprocess
import json
import sys

def test_agent_basic_call():
    """Test that agent returns valid JSON with answer and tool_calls"""
    result = subprocess.run(
        [sys.executable, 'agent.py', 'What is REST?'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, f'Invalid JSON output: {result.stdout}'
    
    assert 'answer' in output
    assert isinstance(output['answer'], str)
    assert 'tool_calls' in output
    assert isinstance(output['tool_calls'], list)
    assert len(output['tool_calls']) == 0
