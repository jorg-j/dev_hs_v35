
import base64
import copy
import datetime
import decimal
import gc
import inspect
import io
import json
import logging
import os
import re
import uuid
import random
from collections import defaultdict
from dataclasses import dataclass
from string import Template
from typing import Any
from uuid import UUID
from enum import Enum
import openpyxl
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Border, Color, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.worksheet.table import Table, TableStyleInfo

from typing import Any, Dict, List

logging.basicConfig(
    encoding="utf-8",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(name)s: Line: %(lineno)s - %(funcName)s(): %(message)s",
    filename='dev_log.log'
)



def _main_validation(document_data, full_page_raw, doc_title_output):
    #IMPORTS
    
    def log_info(text):
        logging.info(text)

    def log_warn(text):
        logging.warn(text)

    def log_debug(text):
        logging.debug(text)

    
    try:
        customer_data = document_data.get("customer")
        customer_data = customer_data[0]
        doc_titles = doc_title_output
    except:
        customer_data = doc_title_output['customer'][0]
        doc_titles = doc_title_output['titles']

    #MAINLINE

    #MAINBLOCK

  
    return return_data
