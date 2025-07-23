# -*- coding: utf-8 -*-
"""
Created on Mon May 31 12:02:54 2021

@author: Paulson
"""
import json
import os
import logging.config

class StdOutLevelFilter(object):
    def __init__(self, level):
        self.level = getattr(logging, level)

    def filter(self, record):
        return record.levelno <= self.level

# Check if the directory already exists
if not os.path.exists("logs"):
    # Create the directory
    os.makedirs("logs")
    print("Directory created successfully!")

with open("logger.json", "r") as f:
    json_config = json.load(f)
    logging.config.dictConfig(json_config)

logger = logging.getLogger("root")

logger.info("Imported the logging module")

if __name__ == "__main__":
    # Redirect print statements to the logger
    print("This is a print statement")
    logger.debug("Testing the errorLogging Module")
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is a error message')
