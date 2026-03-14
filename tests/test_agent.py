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

def test_merge_conflict():
    """Test that agent finds merge conflict info in wiki"""
    result = subprocess.run(
        [sys.executable, 'agent.py', 'How do you resolve a merge conflict?'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, f'Invalid JSON output: {result.stdout}'
    
    assert 'answer' in output
    assert 'source' in output
    assert 'wiki/git.md' in output['source'] or 'wiki/git-workflow.md' in output['source']
    assert len(output['tool_calls']) > 0
    
    # Check that tool calls include read_file
    tools_used = [t['tool'] for t in output['tool_calls']]
    assert 'read_file' in tools_used

def test_list_wiki():
    """Test that agent can list wiki files"""
    result = subprocess.run(
        [sys.executable, 'agent.py', 'What files are in the wiki directory?'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, f'Invalid JSON output: {result.stdout}'
    
    assert 'answer' in output
    assert len(output['tool_calls']) > 0
    
    # Should have used list_files
    tools_used = [t['tool'] for t in output['tool_calls']]
    assert 'list_files' in tools_used
def test_backend_framework():
    result = subprocess.run([sys.executable, 'agent.py', 'What framework does the backend use?'], capture_output=True, text=True)
    output = json.loads(result.stdout)
    assert 'FastAPI' in output['answer']
    assert any(t['tool'] == 'read_file' for t in output['tool_calls'])

def test_item_count():
    result = subprocess.run([sys.executable, 'agent.py', 'How many items are in the database?'], capture_output=True, text=True)
    output = json.loads(result.stdout)
    assert any(t['tool'] == 'query_api' for t in output['tool_calls'])
    assert '0' in output['answer'] or 'items' in output['answer']