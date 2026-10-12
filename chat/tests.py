from unittest.mock import patch
from django.test import TestCase, Client
from chat.backends.agentic_online import (
    calculate as online_calculate,
    get_current_time as online_time,
    get_weather as online_weather,
    reverse_text as online_reverse,
    run_system_command
)
from chat.backends.agentic_offline import (
    calculate as offline_calculate,
    get_current_time as offline_time,
    reverse_text as offline_reverse
)


class GenAIStudioGroupedTests(TestCase):
    def setUp(self):
        self.client = Client()

    # =================================================================
    # GROUP 1: GenAI Chat
    # =================================================================
    def test_group1_online_chat_ui(self):
        res = self.client.get('/chat/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "GenAI")

    def test_group1_offline_chat_ui(self):
        res = self.client.get('/chat/offline/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "GenAI")

    @patch('chat.views.generate_online_chat')
    def test_group1_online_chat_api(self, mock_chat):
        mock_chat.return_value = {"reply": "Online Gemini reply", "type": "genai_online"}
        res = self.client.get('/chat/api?q=hello')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], "Online Gemini reply")

    @patch('chat.views.generate_offline_chat')
    def test_group1_offline_chat_api(self, mock_chat):
        mock_chat.return_value = {"reply": "Offline Ollama reply", "type": "genai_offline"}
        res = self.client.get('/chat/offline/api?q=hello&model=llama3.2')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], "Offline Ollama reply")

    # =================================================================
    # GROUP 2: Agentic AI Online
    # =================================================================
    def test_group2_limited_agent_ui(self):
        res = self.client.get('/chat/agent/limited/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Agentic AI Online")

    def test_group2_universal_agent_ui(self):
        res = self.client.get('/chat/agent/universal/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Agentic AI Online")

    def test_group2_limited_tools(self):
        self.assertEqual(online_calculate("25 * 4"), "100")
        self.assertTrue(len(online_time()) >= 10)
        self.assertIn("18°C", online_weather("Tokyo"))
        self.assertEqual(online_reverse("hello"), "olleh")

    def test_group2_universal_tool(self):
        with patch('subprocess.run') as mock_sub:
            mock_sub.return_value.stdout = "75"
            mock_sub.return_value.stderr = ""
            mock_sub.return_value.returncode = 0
            self.assertEqual(run_system_command("Get-Battery"), "75")

    @patch('chat.views.run_online_limited_agent')
    def test_group2_limited_agent_api(self, mock_agent):
        mock_agent.return_value = {
            "reply": "It is 12:00",
            "steps": [{"tool": "get_current_time", "output": "12:00"}],
            "type": "agentic_online_limited"
        }
        res = self.client.get('/chat/agent/limited/api?q=what+time')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], "It is 12:00")

    @patch('chat.views.propose_universal_action')
    def test_group2_universal_agent_propose(self, mock_propose):
        mock_propose.return_value = {
            "needs_confirmation": True,
            "command": "Get-Process",
            "tool": "run_powershell_command",
            "type": "agentic_online_universal"
        }
        res = self.client.get('/chat/agent/universal/api?q=show+processes&confirmed=false')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["needs_confirmation"])
        self.assertEqual(res.json()["command"], "Get-Process")

    @patch('chat.views.execute_confirmed_command')
    def test_group2_universal_agent_execute_confirmed_password(self, mock_exec):
        mock_exec.return_value = {
            "needs_confirmation": False,
            "reply": "Command output",
            "steps": [{"tool": "run_powershell_command", "output": "done"}],
            "type": "agentic_online_universal"
        }
        res = self.client.get('/chat/agent/universal/api?q=show+processes&confirmed=true&command=Get-Process&password=admin123')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], "Command output")

    @patch('chat.views.execute_confirmed_command')
    def test_group2_universal_agent_invalid_password_returns_403(self, mock_exec):
        mock_exec.side_effect = PermissionError("Access Denied: Incorrect password")
        res = self.client.get('/chat/agent/universal/api?q=show+processes&confirmed=true&command=Get-Process&password=wrong')
        self.assertEqual(res.status_code, 403)
        self.assertTrue(res.json().get("auth_error"))

    # =================================================================
    # GROUP 3: Agentic AI Offline
    # =================================================================
    def test_group3_offline_agent_ui(self):
        res = self.client.get('/chat/agent/offline/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Agentic AI Offline")

    def test_group3_offline_tools(self):
        self.assertEqual(offline_calculate("50 + 50"), "100")
        self.assertTrue(len(offline_time()) >= 10)
        self.assertEqual(offline_reverse("offline"), "enilffo")

    @patch('chat.views.run_offline_agent')
    def test_group3_offline_agent_api(self, mock_agent):
        mock_agent.return_value = {
            "reply": "Calculation is 100",
            "steps": [{"tool": "calculate", "args": {"expression": "50+50"}, "output": "100"}],
            "type": "agentic_offline"
        }
        res = self.client.get('/chat/agent/offline/api?q=calculate+50%2B50&model=llama3.2')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], "Calculation is 100")

    # =================================================================
    # Backward compatibility routes
    # =================================================================
    def test_backward_compatible_routes(self):
        res1 = self.client.get('/chat/limited-agent/')
        self.assertEqual(res1.status_code, 200)
        res2 = self.client.get('/chat/universal-agent/')
        self.assertEqual(res2.status_code, 200)
        res3 = self.client.get('/chat/agent/')
        self.assertEqual(res3.status_code, 200)
