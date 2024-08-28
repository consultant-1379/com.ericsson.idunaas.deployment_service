""""This module implements a helper class to deals with yaml files"""

import logging
import glob
import yaml

LOG = logging.getLogger(__name__)

def load_yaml_document_from_file(filename):
    """
    YAML file can contains multiple documents separated by a triple dash.
    This function return a list of all the documents inside a YAML file. In case of
    a regular file with only one document, it returns a list of one element.
    Each document is a pyhton data structure suitable to represent the document (usually
    is a dictionary)
    :param filename: Path of the YAML file
    :return: A list of python's data structure corresponding to the documents in the
             loaded YAML (usually a dictionary)
    """
    yaml_document_in_file = []
    with open(filename, "rb") as file:
        try:
            for config in yaml.safe_load_all(file):
                yaml_document_in_file.append(config)
        except Exception as excpt:
            logging.info(f'{filename} seems to not be a valid YAML')
            LOG.info(excpt)

    return yaml_document_in_file

def extract_images(data, image_set, keys):
    """
    This function parse a python dictionary analyzing each key and
    looking for docker images.
    :param data: the data to parse.
    :param image_set: a set to fill with the results
    :param keys: the list of keys that will be looked for by the function

    If the keys is a list containing the word 'image', the following dictionaries
    will be correctly recognized:
      { "image": "mydockerimage:mytag" }
      { "image": { "repository": "myrepo", "tag": "mytag" } }
    and the image_set will be:
      ["mydockerimage:mytag", "myrepo:mytag"]
    """
    if isinstance(data, list):
        for value in data:
            extract_images(value, image_set, keys)
    elif isinstance(data, dict):
        for key, value in data.items():
            if key in keys:
                if isinstance(value, str):
                    image_set.add(value)
                elif isinstance(value, dict):
                    logging.debug(f"'image': {value}")
                    if "repository" in value and "tag" in value:
                        image_str = value["repository"]+':'+value["tag"]
                        image_set.add(image_str)
                else:
                    logging.info(f'Skipping -->{value}<-- because is not str nor dict')
            extract_images(value, image_set, keys)

def get_image_from_template(foldername, blacklist):
    """
    This function will create a set of images read from the template
    """
    image_set = set()
    for filename in glob.glob(foldername+'/*.yaml'):
        logging.debug(f'filename={filename} balcklist={blacklist}')
        if filename in blacklist:
            logging.info(f"Skipping file {filename} because it is in blacklist")
            continue
        for data in load_yaml_document_from_file(filename):
            extract_images(data, image_set, ["image"])
    return image_set


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
