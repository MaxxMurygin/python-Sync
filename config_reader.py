import logging
from configparser import ConfigParser


def getconfig(section, filename='ftp.ini'):
    parser = ConfigParser()
    parser.read(filename)
    conf = {}
    try:
        for item in parser.items(section):
            conf[item[0]] = item[1]
    except Exception as err:
        logging.error(str(err))
        return
    return conf
