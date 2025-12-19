"""Integration tests for TUI."""

import pytest
from kai_code.tui.app import KaiCodeApp


@pytest.mark.asyncio
async def test_app_launches():
    """App can launch and exit."""
    app = KaiCodeApp()
    async with app.run_test() as pilot:
        assert app.title == "kai-code"
        # Let the app initialize
        await pilot.pause(0.1)


@pytest.mark.asyncio
async def test_app_has_widgets():
    """App has all required widgets."""
    app = KaiCodeApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.1)

        from kai_code.tui.widgets import MessageList, InputArea, StatusBar, ToolPanel

        # Check widgets are present on the screen
        screen = app.screen
        message_list = screen.query_one("#message-list", MessageList)
        assert message_list is not None

        input_area = screen.query_one("#input-area", InputArea)
        assert input_area is not None

        status_bar = screen.query_one("#status-bar", StatusBar)
        assert status_bar is not None

        tool_panel = screen.query_one("#tool-panel", ToolPanel)
        assert tool_panel is not None


@pytest.mark.asyncio
async def test_yolo_mode_initialization():
    """YOLO mode is initialized correctly."""
    app_yolo = KaiCodeApp(yolo=True)
    assert app_yolo._yolo is True

    app_no_yolo = KaiCodeApp(yolo=False)
    assert app_no_yolo._yolo is False


@pytest.mark.asyncio
async def test_model_initialization():
    """Model is initialized correctly."""
    app = KaiCodeApp(model="test-model")
    assert app._model == "test-model"


@pytest.mark.asyncio
async def test_session_initialization():
    """Session is initialized correctly."""
    app = KaiCodeApp(session="test-session")
    assert app._session == "test-session"


@pytest.mark.asyncio
async def test_command_registry():
    """App has command registry."""
    app = KaiCodeApp()
    assert app._commands is not None
    assert app._commands.is_valid("help") is True
    assert app._commands.is_valid("exit") is True
    assert app._commands.is_valid("yolo") is True
    assert app._commands.is_valid("clear") is True
    assert app._commands.is_valid("model") is True
    assert app._commands.is_valid("session") is True


@pytest.mark.asyncio
async def test_yolo_state_changes():
    """YOLO mode state can be changed."""
    app = KaiCodeApp(yolo=False)
    assert app._yolo is False

    # Change it
    app._yolo = True
    assert app._yolo is True

    # Change it back
    app._yolo = False
    assert app._yolo is False


@pytest.mark.asyncio
async def test_model_state_changes():
    """Model state can be changed."""
    app = KaiCodeApp(model="default")
    assert app._model == "default"

    # Change model
    app._model = "gpt-4"
    assert app._model == "gpt-4"
