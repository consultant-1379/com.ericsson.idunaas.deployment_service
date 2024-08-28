"""
Unit Tests for the AWS Deployment Manager module.
"""

import getpass

import pytest

from cli_test_helpers import ArgvContext

from aws_deployment_manager import aws_deployment_manager as manager, utils
from aws_deployment_manager.commands.configure import ConfigureManager
from aws_deployment_manager.commands.delete import DeleteManager
from aws_deployment_manager.commands.generate import GenerateManager
from aws_deployment_manager.commands.getconfig import GetconfigManager
from aws_deployment_manager.commands.install import InstallManager
from aws_deployment_manager.commands.prepare import PrepareManager
from aws_deployment_manager.commands.update import UpdateManager
from aws_deployment_manager.commands.validate import ValidateManager


# pylint: disable=no-self-use
# pylint: disable=no-value-for-parameter
@pytest.mark.usefixtures("setup_config_file")
class TestAWSDeploymentManager:
    """
    Class to run tests for the AWS Deployment Manager module.
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self):
        """
        Sets up config for running tests and cleans up after the tests are done.
        """
        yield
        manager.input = input

    @staticmethod
    def method_raises_exception_mock(*args):
        """
        Mock function that raises an exception. Used for negative tests.
        :param args:
        """
        raise Exception('This is a good failure!')

    @staticmethod
    def method_does_nothing_mock(*args):
        """
        Mock function that does nothing successfully
        :param args:
        :return: a string
        :rtype: String
        """
        return 'this does nothing'

    @staticmethod
    def method_with_kwargs_mock(**kwargs):
        """
        Mock function that if user_input is passed in will reply yes or no depending on its
        value
        :param kwargs:
        """
        for key, value in kwargs.items():
            if key == 'user_input':
                if value:
                    return 'yes'
                return 'no'
        return 'meaningless mocked return'

    def test_prepare(self, monkeypatch):
        """
        Tests the prepare command runs successfully.
        :param monkeypatch:
        """
        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(PrepareManager, "prepare_config_file", self.method_does_nothing_mock)
        with ArgvContext('aws_deployment_manager'), pytest.raises(SystemExit) as exit_exception:
            manager.prepare()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0

    def test_prepare_failure(self, monkeypatch):
        """
        Tests that we catch an exception raised by the prepare command.
        :param monkeypatch:
        """
        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(PrepareManager, "prepare_config_file",
                            self.method_raises_exception_mock)
        with ArgvContext('aws_deployment_manager', '-v', '0'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.prepare()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 1

    def test_generate(self, monkeypatch):
        """
        Tests the generate command runs successfully.
        :param monkeypatch:
        """
        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(GenerateManager, "generate_config_file", self.method_does_nothing_mock)
        with ArgvContext('aws_deployment_manager', '-e', 'idun-2', '-r', 'eu-west-1'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.generate()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0

    def test_generate_failure(self, monkeypatch):
        """
        Tests that we catch an exception raised by the generate command.
        :param monkeypatch:
        """
        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(GenerateManager, "generate_config_file",
                            self.method_raises_exception_mock)
        with ArgvContext('aws_deployment_manager', '-e', 'idun-2', '-r', 'eu-west-1'),\
             pytest.raises(SystemExit) as exit_exception:
            manager.generate()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 1

    def test_validate(self, monkeypatch):
        """
        Tests the validate command runs successfully.
        :param monkeypatch:
        """
        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(ValidateManager, "validate_config", self.method_does_nothing_mock)
        with ArgvContext('aws_deployment_manager'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.validate()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0

    def test_validate_failure(self, monkeypatch):
        """
        Tests that we catch an exception raised by the validate command.
        :param monkeypatch:
        """
        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(ValidateManager, "validate_config", self.method_raises_exception_mock)
        with ArgvContext('aws_deployment_manager'),\
             pytest.raises(SystemExit) as exit_exception:
            manager.validate()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 1

    def test_install(self, monkeypatch):
        """
        Tests the install command runs successfully.
        :param monkeypatch:
        """
        successful_method_was_called = False

        def check_method_was_called_mock(*args):
            """
            Mock function that if called will set successful_method_was_called to True
            :param args:
            """
            nonlocal successful_method_was_called
            successful_method_was_called = True

        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(manager, "check_and_ask_confirm_option", self.method_with_kwargs_mock)
        monkeypatch.setattr(manager, "check_and_ask_username_option", self.method_with_kwargs_mock)
        monkeypatch.setattr(manager, "check_and_ask_password_option", self.method_with_kwargs_mock)
        monkeypatch.setattr(utils, "test_docker_registry_login", self.method_does_nothing_mock)
        monkeypatch.setattr(InstallManager, "pre_install", self.method_does_nothing_mock)
        monkeypatch.setattr(InstallManager, "install", check_method_was_called_mock)
        monkeypatch.setattr(InstallManager, "post_install", self.method_does_nothing_mock)

        with ArgvContext('aws_deployment_manager', '-u', 'username', '-p', 'password'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.install()
        assert successful_method_was_called is False
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0

        with ArgvContext('aws_deployment_manager', '--yes', '-u', 'username', '-p', 'password'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.install()
        assert successful_method_was_called is True
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0

        monkeypatch.setattr(InstallManager, "install", self.method_raises_exception_mock)

        with ArgvContext('aws_deployment_manager', '--yes', '-u', 'username', '-p', 'password'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.install()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 1

    def test_configure(self, monkeypatch):
        """
        Tests the configure command runs successfully.
        :param monkeypatch:
        """
        successful_method_was_called = False

        def check_method_was_called_mock(*args):
            """
            Mock function that if called will set successful_method_was_called to True
            :param args:
            """
            nonlocal successful_method_was_called
            successful_method_was_called = True

        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(manager, "check_and_ask_confirm_option", self.method_with_kwargs_mock)
        monkeypatch.setattr(ConfigureManager, "configure", check_method_was_called_mock)

        with ArgvContext('aws_deployment_manager'), pytest.raises(SystemExit) as exit_exception:
            manager.configure()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 2
        assert successful_method_was_called is False

        with ArgvContext('aws_deployment_manager', '--yes', '--namespace', 'eiap_namespace'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.configure()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0
        assert successful_method_was_called is True

        monkeypatch.setattr(ConfigureManager, "configure", self.method_raises_exception_mock)

        with ArgvContext('aws_deployment_manager', '--yes', '--namespace', 'eiap_namespace'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.configure()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 1

    def test_update(self, monkeypatch):
        """
        Tests the update command runs successfully.
        :param monkeypatch:
        """
        successful_method_was_called = False

        def check_method_was_called_mock(*args):
            """
            Mock function that if called will set successful_method_was_called to True
            :param args:
            """
            nonlocal successful_method_was_called
            successful_method_was_called = True

        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(manager, "check_and_ask_confirm_option", self.method_with_kwargs_mock)
        monkeypatch.setattr(UpdateManager, "update", check_method_was_called_mock)

        with ArgvContext('aws_deployment_manager'), pytest.raises(SystemExit) as exit_exception:
            manager.update()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0
        assert successful_method_was_called is False

        with ArgvContext('aws_deployment_manager', '--yes'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.update()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0
        assert successful_method_was_called is True

        monkeypatch.setattr(UpdateManager, "update", self.method_raises_exception_mock)

        with ArgvContext('aws_deployment_manager', '--yes'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.update()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 1

    def test_delete(self, monkeypatch):
        """
        Tests the delete command runs successfully.
        :param monkeypatch:
        """
        successful_method_was_called = False

        def check_method_was_called_mock(*args):
            """
            Mock function that if called will set successful_method_was_called to True
            :param args:
            """
            nonlocal successful_method_was_called
            successful_method_was_called = True

        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(manager, "check_and_ask_confirm_option", self.method_with_kwargs_mock)
        monkeypatch.setattr(DeleteManager, "delete", check_method_was_called_mock)

        with ArgvContext('aws_deployment_manager', '-e', 'idun-2', '-r', 'eu-west-1'),\
                pytest.raises(SystemExit) as exit_exception:
            manager.delete()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0
        assert successful_method_was_called is False

        with ArgvContext('aws_deployment_manager', '-e', 'idun-2', '-r', 'eu-west-1', '--yes'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.delete()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0
        assert successful_method_was_called is True

        monkeypatch.setattr(DeleteManager, "delete", self.method_raises_exception_mock)

        with ArgvContext('aws_deployment_manager', '-e', 'idun-2', '-r', 'eu-west-1', '--yes'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.delete()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 1

    def test_getconfig(self, monkeypatch):
        """
        Tests the getconfig command runs successfully.
        :param monkeypatch:
        """
        successful_method_was_called = False

        def check_method_was_called_mock(*args):
            """
            Mock function that if called will set successful_method_was_called to True
            :param args:
            """
            nonlocal successful_method_was_called
            successful_method_was_called = True

        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(GetconfigManager, "generate_k8s_config_file",
                            check_method_was_called_mock)

        with ArgvContext('aws_deployment_manager', '-e', 'idun-2', '-r', 'eu-west-1'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.getconfig()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0
        assert successful_method_was_called is True

        monkeypatch.setattr(GetconfigManager, "generate_k8s_config_file",
                            self.method_raises_exception_mock)

        with ArgvContext('aws_deployment_manager', '-e', 'idun-2', '-r', 'eu-west-1'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.getconfig()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 1

    def test_run(self, monkeypatch):
        """
        Tests the run command runs successfully.
        :param monkeypatch:
        """
        successful_method_was_called = False

        def check_method_was_called_mock(command):
            """
            Mock function that if called will set successful_method_was_called to True
            :param command:
            """
            nonlocal successful_method_was_called
            successful_method_was_called = True

        monkeypatch.setattr(utils, "initialize_logging", self.method_with_kwargs_mock)
        monkeypatch.setattr(utils, "execute_command", check_method_was_called_mock)

        with ArgvContext('aws_deployment_manager', '-c', 'echo "hello"'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.run()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 0
        assert successful_method_was_called is True

        monkeypatch.setattr(utils, "execute_command", self.method_raises_exception_mock)

        with ArgvContext('aws_deployment_manager', '-c', 'echo "hello"'), \
                pytest.raises(SystemExit) as exit_exception:
            manager.run()
        assert exit_exception.type == SystemExit
        assert exit_exception.value.code == 1

    def test_check_and_ask_confirm_option(self):
        """
        Tests the check_and_ask_confirm_option function runs successfully.
        """
        mock_reply = 'yes'

        def input_mock(question):
            """
            Mock function of input that will reply with the global variable mock_reply value
            :param question:
            """
            nonlocal mock_reply
            return mock_reply

        reply = manager.check_and_ask_confirm_option(True, 'Some question?')
        assert reply == 'yes'

        manager.input = input_mock
        reply = manager.check_and_ask_confirm_option(False, 'Some question?')
        assert reply == 'yes'

        mock_reply = 'y'
        reply = manager.check_and_ask_confirm_option(False, 'Some question?')
        assert reply == 'y'

        mock_reply = 'no'
        reply = manager.check_and_ask_confirm_option(False, 'Some question?')
        assert reply == 'no'

        mock_reply = 'n'
        reply = manager.check_and_ask_confirm_option(False, 'Some question?')
        assert reply == 'n'

    def test_check_and_ask_username_option(self):
        """
        Tests the if we pass in a username, no username is asked and that if we don't pass a
        username, it queries the user for a username.
        """

        def input_mock(question):
            """
            Mock function of input that will reply with a mock username
            :param question:
            """
            return 'another_username'

        reply = manager.check_and_ask_username_option('some_username')
        assert reply == 'some_username'

        manager.input = input_mock
        reply = manager.check_and_ask_username_option(None)
        assert reply == 'another_username'

    def test_check_and_ask_password_option(self, monkeypatch):
        """
        Tests the if we pass in a password, no password is asked and that if we don't pass a
        password, it queries the user for a password.
        :param monkeypatch:
        """

        def getpass_mock(prompt):
            """
            Mock function of getpass that will reply with a mock password
            :param prompt:
            """
            return 'another_password'

        reply = manager.check_and_ask_password_option('some_password')
        assert reply == 'some_password'

        monkeypatch.setattr(getpass, "getpass", getpass_mock)
        reply = manager.check_and_ask_password_option(None)
        assert reply == 'another_password'
