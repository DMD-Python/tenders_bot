import unittest
from unittest.mock import MagicMock, patch

from django.test import TestCase

from tenders_bot.telegram import NavData, navigate, send_node


class TestTelegramBot(TestCase):

    @patch('tenders_bot.telegram.bot.send_message')
    @patch('tenders_bot.telegram.reset_state')
    @patch('tenders_bot.models.Node')
    def test_send_node_with_text(self, mock_node, mock_reset_state, mock_send_message):
        # Mock node with text, no files, and no input function
        mock_node_instance = MagicMock()
        mock_node_instance.text = "Test node"
        mock_node_instance.files.all.return_value = []
        mock_node_instance.child_nodes.all.return_value = []
        mock_node_instance.input_function = None

        # Call function to test
        send_node(12345, mock_node_instance, only_nav=False)

        # Assertions
        mock_reset_state.assert_called_once_with(12345)  # Ensure state is reset
        mock_send_message.assert_called_once_with(12345, "Test node", parse_mode="HTML", disable_web_page_preview=True)

    @patch('tenders_bot.telegram.bot.send_document')
    @patch('tenders_bot.telegram.bot.send_message')
    @patch('tenders_bot.models.Node')
    def test_send_node_with_files(self, mock_node, mock_send_message, mock_send_document):
        # Mock node with files
        mock_node_instance = MagicMock()
        mock_file = MagicMock()
        mock_file.file = "test_file"
        mock_node_instance.files.all.return_value = [mock_file]

        # Call function to test
        send_node(12345, mock_node_instance, only_nav=False)

        # Assertions
        mock_send_message.assert_any_call(12345, "Отправляем файлы, подождите немного...")
        mock_send_document.assert_called_with(12345, "test_file")  # Ensure file is sent

    @patch('tenders_bot.telegram.NavData.deserialize')
    @patch('tenders_bot.telegram.bot.edit_message_text')
    def test_navigate_forward(self, mock_edit_message_text, mock_deserialize):
        # Mocking NavData and its output
        mock_nav_data = MagicMock()
        mock_nav_data.nav_to_node = MagicMock()
        mock_nav_data.nav_to_node.button_text = "Forward"
        mock_nav_data.direction = 'f'

        mock_deserialize.return_value = mock_nav_data

        # Mocking the call object
        mock_call = MagicMock()
        mock_call.message.text = "Original Text"
        mock_call.message.chat.id = 12345
        mock_call.message.id = 6789

        # Call function to test
        navigate(mock_call)

        # Assertions: Check if text was modified correctly
        mock_edit_message_text.assert_called_once_with(
            "Original Text\n\n> Forward", 12345, 6789
        )

    @patch('tenders_bot.telegram.NavData.deserialize')
    @patch('tenders_bot.telegram.bot.edit_message_text')
    def test_navigate_back(self, mock_edit_message_text, mock_deserialize):
        # Mocking NavData and its output
        mock_nav_data = MagicMock()
        mock_nav_data.nav_to_node = MagicMock()
        mock_nav_data.nav_to_node.button_text = "Backward"
        mock_nav_data.direction = 'b'

        mock_deserialize.return_value = mock_nav_data

        # Mocking the call object
        mock_call = MagicMock()
        mock_call.message.text = "Original Text"
        mock_call.message.chat.id = 12345
        mock_call.message.id = 6789

        # Call function to test
        navigate(mock_call)

        # Assertions: Check if text was modified correctly
        mock_edit_message_text.assert_called_once_with(
            "Original Text\n\n> Назад", 12345, 6789
        )

    def test_navdata_serialize(self):
        # Test serialization logic
        mock_node = MagicMock()
        mock_node.id = 123
        nav_data = NavData(nav_to_node=mock_node, direction='f')

        serialized = nav_data.serialize()
        expected = "nav:123|f"
        self.assertEqual(serialized, expected)  # Ensure correct serialization format

    def test_navdata_deserialize_valid_data(self):
        # Setup mock node object
        mock_node = MagicMock()
        with patch('tenders_bot.models.Node.objects.get') as mock_get:
            mock_get.return_value = mock_node

            # Test valid data
            data = "nav:123|f"
            nav_data = NavData.deserialize(data)

            self.assertEqual(nav_data.nav_to_node, mock_node)
            self.assertEqual(nav_data.direction, "f")

    def test_navdata_deserialize_invalid_data(self):
        # Test invalid data
        with self.assertRaises(ValueError):
            NavData.deserialize("invalid_data")

    def test_navdata_check(self):
        # Test check function for valid and invalid data
        self.assertTrue(NavData.check("nav:123|f"))
        self.assertFalse(NavData.check("invalid"))


if __name__ == '__main__':
    unittest.main()
