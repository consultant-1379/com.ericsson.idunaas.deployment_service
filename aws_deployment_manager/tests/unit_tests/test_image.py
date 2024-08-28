"""
Unit Tests for the backup module.
"""

import pytest

import aws_deployment_manager.commands.image as image

# pylint: disable=no-self-use, protected-access, unused-argument, unused-variable, trailing-whitespace, trailing-newlines
@pytest.mark.usefixtures("setup_config_file")
class TestImage:
    """
    Class to run tests for the image module.
    """
    def test__substitute_images(self):
        """Test image substitution"""
        generic_list = ['REP1/test1', 'REP2/test2']
        main_list = image._substitute_registry(
                        generic_list, dict(REP1='repo1',REP2='repo2'))
        assert main_list[0] == "repo1/test1"
        assert main_list[1] == "repo2/test2"

    def test__image_as_dict(self):
        """Test splitting image in repo:tag"""
        img = image._image_as_dict('repo:tag')
        assert isinstance(img, dict)
        assert img['repository'] == 'repo'
        assert img['tag'] == 'tag'
