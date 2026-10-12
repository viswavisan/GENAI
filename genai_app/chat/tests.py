from unittest.mock import patch
from django.test import TestCase, Client
from chat.backends.limited_agent import calculate, get_current_time, get_weather, reverse_text
from chat.backends.universal_agent import run_system_command


class ModularGenAITests(TestCase):
    def setUp(self):
        self.client = Client()

    # 1. UI Renders
    def test_standard_ui_renders(self):
        response = self.client.get('/chat/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Standard Chat")

    def test_offline_ui_renders(self):
        response = self.client.get('/chat/offline/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Offline Model")

    def test_limited_agent_ui_renders(self):
        response = self.client.get('/chat/limited-agent/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Limited Agent")

    def test_universal_agent_ui_renders(self):
        response = self.client.get('/chat/universal-agent/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Universal Agent")

    # 2. Backends unit tests
    def test_limited_agent_tools(self):
        self.assertEqual(calculate("25 * 4"), "100")
        self.assertTrue(len(get_current_time()) >= 10)
        self.assertIn("18°C", get_weather("Tokyo"))
        self.assertEqual(reverse_text("python"), "nohtyp")

    def test_universal_agent_tool(self):
        with patch('subprocess.run') as mock_sub:
            mock_sub.return_value.stdout = "75"
            mock_sub.return_value.stderr = ""
            mock_sub.return_value.returncode = 0
            self.assertEqual(run_system_command("Get-Battery"), "75")

    # 3. API endpoints
    @patch('chat.views.generate_standard_reply')
    def test_standard_api(self, mock_reply):
        mock_reply.return_value = {"reply": "Hello standard", "type": "standard_online"}
        response = self.client.get('/chat/api?q=hello')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Hello standard")

    @patch('chat.views.generate_offline_reply')
    def test_offline_api(self, mock_offline):
        mock_offline.return_value = {"reply": "Hello offline", "type": "offline_local"}
        response = self.client.get('/chat/offline/api?q=hello&model=llama3.2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Hello offline")

    @patch('chat.views.run_limited_agent')
    def test_limited_agent_api(self, mock_limited):
        mock_limited.return_value = {
            "reply": "Time is 10:00",
            "steps": [{"tool": "get_current_time", "output": "10:00"}],
            "type": "limited_agent"
        }
        response = self.client.get('/chat/limited-agent/api?q=what+time')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Time is 10:00")

    @patch('chat.views.propose_universal_action')
    def test_universal_agent_propose_confirmation(self, mock_propose):
        mock_propose.return_value = {
            "needs_confirmation": True,
            "command": "Get-Process",
            "tool": "run_system_command",
            "type": "universal_agent"
        }
        response = self.client.get('/chat/universal-agent/api?q=show+processes&confirmed=false')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["needs_confirmation"])
        self.assertEqual(response.json()["command"], "Get-Process")

    @patch('chat.views.execute_confirmed_command')
    def test_universal_agent_execute_confirmed_with_password(self, mock_exec):
        mock_exec.return_value = {
            "needs_confirmation": False,
            "reply": "Processes listed.",
            "steps": [{"tool": "run_system_command", "output": "proc list"}],
            "type": "universal_agent"
        }
        response = self.client.get('/chat/universal-agent/api?q=show+processes&confirmed=true&command=Get-Process&password=admin123')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["needs_confirmation"])
        self.assertEqual(response.json()["reply"], "Processes listed.")

    @patch('chat.views.execute_confirmed_command')
    def test_universal_agent_invalid_password_returns_403(self, mock_exec):
        mock_exec.side_effect = PermissionError("Access Denied: Incorrect password")
        response = self.client.get('/chat/universal-agent/api?q=show+processes&confirmed=true&command=Get-Process&password=wrongpass')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.json().get("auth_error"))
        self.assertIn("Access Denied", response.json().get("error"))
