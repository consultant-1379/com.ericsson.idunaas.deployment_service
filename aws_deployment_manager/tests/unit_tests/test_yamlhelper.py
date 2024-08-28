"""
Unit Tests for the YamlHelper module.
"""

import os
import shutil
from aws_deployment_manager import yamlhelper

TEST_FILE_CONTENT = """
image: mydockerimage:mytag
---
image:
  repository: myrepo
  tag: mytag
"""

# pylint: disable=no-self-use
class TestYamlhelper:
    """Test for the module 'yamlhelper'"""

    def __create_test_file(self):
        # script_absolute_path = os.path.abspath(__file__)
        # script_dir = os.path.dirname(script_absolute_path)
        my_testdir = '/tmp/my_test_dir'
        if os.path.exists(my_testdir):
            shutil.rmtree(my_testdir)

        os.mkdir(my_testdir)
        test_filename = my_testdir + '/test.yaml'
        with open(test_filename, 'w') as test_file:
            test_file.write(TEST_FILE_CONTENT)

        return my_testdir, test_filename

    def test_load_document(self):
        """Test loading multiple docs from the same YAML"""
        _ , test_filename = self.__create_test_file()
        doc_list = yamlhelper.load_yaml_document_from_file(test_filename)
        assert len(doc_list) == 2

        assert isinstance(doc_list[0], dict)
        assert doc_list[0]['image'] == 'mydockerimage:mytag'

        assert isinstance(doc_list[1], dict)
        assert isinstance(doc_list[1]['image'], dict)
        assert doc_list[1]['image']['repository'] == "myrepo"
        assert doc_list[1]['image']['tag'] == "mytag"

    def test_get_images(self):
        """Test the split of docker image in repo:tag"""
        my_testdir, _ = self.__create_test_file()
        image_set = yamlhelper.get_image_from_template(my_testdir, [])
        images = ['mydockerimage:mytag', 'myrepo:mytag']
        for img in image_set:
            assert img in images
