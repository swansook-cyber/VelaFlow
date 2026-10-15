"""Static wiring contracts: keep actual song context connected to lyric review.

This does not replace browser/E2E testing; it catches disconnected parameters
without importing Streamlit or hitting any AI provider.
"""
import ast
from pathlib import Path


MAIN = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _function_tree():
    tree = ast.parse(MAIN.read_text(encoding="utf-8-sig"))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    return functions


def test_shared_editor_receives_story_context():
    functions = _function_tree()
    editor = functions["_render_suno_copy_fields"]
    parameters = {argument.arg for argument in editor.args.args}
    assert {"story_idea", "selected_hook"} <= parameters
    reviews = [
        node for node in ast.walk(editor)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "review_thai_story_coherence"
    ]
    assert len(reviews) == 1
    arguments = {keyword.arg: keyword.value for keyword in reviews[0].keywords}
    assert isinstance(arguments["idea"], ast.Name)
    assert arguments["idea"].id == "story_idea"
    assert isinstance(arguments["selected_hook"], ast.Name)
    assert arguments["selected_hook"].id == "selected_hook"


def test_main_song_editor_passes_selected_hook_and_idea():
    functions = _function_tree()
    matches = [
        node for parent in functions.values() for node in ast.walk(parent)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_render_suno_copy_fields"
    ]
    assert len(matches) == 2
    calls = {
        keyword.value.value: node
        for node in matches for keyword in node.keywords
        if keyword.arg == "key_prefix" and isinstance(keyword.value, ast.Constant)
    }
    assert set(calls) == {"simple_song", "quick_song"}
    for node in calls.values():
        named = {keyword.arg for keyword in node.keywords}
        assert {"story_idea", "selected_hook", "lyrics_key", "style_key"} <= named
