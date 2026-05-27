"""Tests for chat session and message endpoints.

Agent calls are mocked so tests don't require a real LLM API key.
"""

from unittest.mock import AsyncMock, patch, MagicMock
from app.models.chat import ChatSession, ChatMessage, ChatMessageRole, ChatMessageStatus
from app.services.llm_service import LLMResponse


def _mock_agent_response(content="Here is your financial summary."):
    return LLMResponse(content=content, model="gemini/gemini-2.5-flash", latency_ms=100)


class TestCreateChatSession:
    def test_create_session_with_title(self, client, auth_headers):
        resp = client.post("/chats", json={"title": "My Budget Chat"}, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["title"] == "My Budget Chat"
        assert data["status"] == "ACTIVE"

    def test_create_session_without_title(self, client, auth_headers):
        resp = client.post("/chats", json={}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["data"]["title"] == "New chat"

    def test_create_requires_auth(self, client):
        resp = client.post("/chats", json={"title": "Test"})
        assert resp.status_code == 401


class TestListChatSessions:
    def test_list_own_sessions(self, client, regular_user, auth_headers, db):
        db.add(ChatSession(user_id=regular_user.id, title="Session 1"))
        db.add(ChatSession(user_id=regular_user.id, title="Session 2"))
        db.commit()

        resp = client.get("/chats", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_list_does_not_return_other_users_sessions(self, client, admin_user, auth_headers, db):
        db.add(ChatSession(user_id=admin_user.id, title="Admin Session"))
        db.commit()

        resp = client.get("/chats", headers=auth_headers)
        assert len(resp.json()["data"]) == 0

    def test_list_requires_auth(self, client):
        resp = client.get("/chats")
        assert resp.status_code == 401


class TestGetChatSession:
    def test_get_own_session(self, client, regular_user, auth_headers, db):
        session = ChatSession(user_id=regular_user.id, title="My Chat")
        db.add(session)
        db.commit()
        db.refresh(session)

        resp = client.get(f"/chats/{session.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == session.id
        assert data["messages"] == []

    def test_get_other_users_session_returns_404(self, client, admin_user, auth_headers, db):
        session = ChatSession(user_id=admin_user.id, title="Admin Chat")
        db.add(session)
        db.commit()
        db.refresh(session)

        resp = client.get(f"/chats/{session.id}", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateChatSession:
    def test_update_title(self, client, regular_user, auth_headers, db):
        session = ChatSession(user_id=regular_user.id, title="Old Title")
        db.add(session)
        db.commit()
        db.refresh(session)

        resp = client.patch(f"/chats/{session.id}", json={"title": "New Title"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "New Title"

    def test_update_empty_title_rejected(self, client, regular_user, auth_headers, db):
        session = ChatSession(user_id=regular_user.id, title="Title")
        db.add(session)
        db.commit()
        db.refresh(session)

        resp = client.patch(f"/chats/{session.id}", json={"title": ""}, headers=auth_headers)
        assert resp.status_code == 422


class TestDeleteChatSession:
    def test_soft_delete_session(self, client, regular_user, auth_headers, db):
        session = ChatSession(user_id=regular_user.id, title="Delete Me")
        db.add(session)
        db.commit()
        db.refresh(session)

        resp = client.delete(f"/chats/{session.id}", headers=auth_headers)
        assert resp.status_code == 200

        list_resp = client.get("/chats", headers=auth_headers)
        assert len(list_resp.json()["data"]) == 0


class TestListMessages:
    def test_list_messages_in_session(self, client, regular_user, auth_headers, db):
        session = ChatSession(user_id=regular_user.id, title="Chat")
        db.add(session)
        db.commit()
        db.refresh(session)

        db.add(ChatMessage(
            session_id=session.id, role=ChatMessageRole.USER, content="Hello",
        ))
        db.add(ChatMessage(
            session_id=session.id, role=ChatMessageRole.ASSISTANT, content="Hi there!",
        ))
        db.commit()

        resp = client.get(f"/chats/{session.id}/messages", headers=auth_headers)
        assert resp.status_code == 200
        messages = resp.json()["data"]
        assert len(messages) == 2
        assert messages[0]["role"] == "USER"
        assert messages[1]["role"] == "ASSISTANT"


class TestCreateMessage:
    def test_send_message_gets_ai_reply(self, client, regular_user, auth_headers, db):
        session = ChatSession(user_id=regular_user.id, title="New chat")
        db.add(session)
        db.commit()
        db.refresh(session)

        with patch(
            "app.services.chat_service.run_finance_agent",
            new_callable=AsyncMock,
            return_value=_mock_agent_response("You spent $200 on food."),
        ), patch(
            "app.services.chat_service.hydrate_chat_memory",
            new_callable=AsyncMock,
        ), patch(
            "app.services.chat_service.get_chat_memory",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.chat_service.append_chat_memory",
            new_callable=AsyncMock,
        ):
            resp = client.post(
                f"/chats/{session.id}/messages",
                json={"content": "How much did I spend on food?"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["user_message"]["content"] == "How much did I spend on food?"
        assert data["assistant_message"]["content"] == "You spent $200 on food."
        assert data["assistant_message"]["role"] == "ASSISTANT"

    def test_send_message_auto_titles_session(self, client, regular_user, auth_headers, db):
        session = ChatSession(user_id=regular_user.id, title="New chat")
        db.add(session)
        db.commit()
        db.refresh(session)

        with patch(
            "app.services.chat_service.run_finance_agent",
            new_callable=AsyncMock,
            return_value=_mock_agent_response("Sure!"),
        ), patch("app.services.chat_service.hydrate_chat_memory", new_callable=AsyncMock), \
           patch("app.services.chat_service.get_chat_memory", new_callable=AsyncMock, return_value=[]), \
           patch("app.services.chat_service.append_chat_memory", new_callable=AsyncMock):
            client.post(
                f"/chats/{session.id}/messages",
                json={"content": "Show me my budget"},
                headers=auth_headers,
            )

        db.refresh(session)
        assert session.title == "Show me my budget"

    def test_send_message_requires_auth(self, client, regular_user, db):
        session = ChatSession(user_id=regular_user.id, title="Chat")
        db.add(session)
        db.commit()
        db.refresh(session)

        resp = client.post(
            f"/chats/{session.id}/messages",
            json={"content": "Hello"},
        )
        assert resp.status_code == 401

    def test_send_empty_message_rejected(self, client, regular_user, auth_headers, db):
        session = ChatSession(user_id=regular_user.id, title="Chat")
        db.add(session)
        db.commit()
        db.refresh(session)

        resp = client.post(
            f"/chats/{session.id}/messages",
            json={"content": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422
