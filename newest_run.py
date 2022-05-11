#!/usr/bin/env python

"""newest_run.py

    Read most recent run from databroker
    ...process and plot the data
"""

import logging
import uuid

logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)

from dotenv import load_dotenv

from databroker import catalog, catalog_search_path
import intake

from bluesky.callbacks import CallbackBase
# from event_model import unpack_event_page

import sys
import os
from os.path import dirname, abspath
import argparse
import requests

from scipy.stats import sem
from numpy import array, ndarray, unique, full, argwhere, isnan
import xarray as xr
import dask.array as da
import pandas as pd
import itertools as it
from time import sleep

import matplotlib.pyplot as plt
import json
from pprint import pprint


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Configure environment
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
load_dotenv()  # import environment variables from .env

catalog_name = "TEST"

# Provide access to locally defined catalog (YML is in the project folder)
# This hides `databroker.catalog`
# catalog = intake.open_catalog("./catalogs.yml")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Functions & globals
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def array_to_str(value):
    '''If value is an array, return it as string representation'''
    if isinstance(value, list) or isinstance(value, ndarray):
        return str(value)
    return value
        
pre_edges = {
    "Fe": {
        "EY SCVM": {
            "energy": [697.5, 699.5],
            }, 
        "LY SCVM": {
            "energy": [701.5, 703.5],
            }, 
        "energy": [697.5, 699.5],
        },
    "Co": {
        "EY SCVM": {
            "energy": [771.5, 773.5],
            }, 
        "LY SCVM": {
            "energy": [773.75, 775.5],
            }, 
        "energy": [771.5, 773.5],
        },
    }
def is_subrange_of(subrange, full_range):
    '''Is subrange in full_range?
    subrange: subrange to test; list(float); len()==2
    full_range: encompassing range; list(float); len()==2
    RETURNS: True if subrange is encompassed by full_range
    '''
    _subrange = subrange.copy()
    _subrange.sort()
    _full_range = full_range.copy()
    _full_range.sort()

    return (
        (_subrange[0] >= _full_range[0]) and
        (_subrange[-1] <= _full_range[-1])
        )

def get_pre_edge(map, name, signal=None):
    '''Is subrange in full_range?
    map: map of named pre-edge ranges; nested dict
    name: name of pre-edge range
    signal: name of signal, for signal-dependent range;
            Use default range if signal not found
    RETURNS: energy range of pre-edge
    '''
    ranges = map.get(name, None)
    if not ranges:
        return [None, None]
    
    pre_edge_range = ranges.get(signal, ranges)

    return pre_edge_range["energy"]

class ApiCallback(CallbackBase):
    def __init__(self, host='127.0.0.1', port=8000, **kwargs):
        super().__init__(**kwargs)
        self.url = f"http://{host}:{port}"
    def start(self, doc):
        # print("I got a new 'start' Document")
        pprint(doc)
        r = requests.post(
            f"{self.url}/start", 
            # data={"start": doc},
            # data=json.dumps(doc),
            json=json.dumps(doc),
            )
        r.raise_for_status()
    def descriptor(self, doc):
        # print("I got a new 'descriptor' Document")
        pass
    def event(self, doc):
        # print("I got a new 'event' Document")
        r = requests.post(
            f"{self.url}/event", 
            # data={"event": doc},
            # data=json.dumps(doc),
            json=json.dumps(doc),
            )
        r.raise_for_status()
    def stop(self, doc):
        # print("I got a new 'stop' Document")
        pass

class ApiDelayedCallback(ApiCallback):
    # def event_page(self, doc):
    #     for event in unpack_event_page(doc):
    #         print("I got a new 'event' Document")
    #     # Do something
    def __init__(self, delay=0.5, **kwargs):
        super().__init__(**kwargs)
        self.delay = delay
        self.seq_gen = it.count(1)
    def event(self, doc):
        data_item = next(iter(doc["data"].values()))
        if type(data_item) is list:
            print("...array_event") 
            for i in range(len(data_item)):
                new_event = {
                    key: value for key, value in doc.items()
                    if not key=="data"
                    }
                new_event["uid"] = str(uuid.uuid4())
                new_event["seq_num"] = next(self.seq_gen)
                # print(f'...{new_event["seq_num"]}', end='')
                new_event["data"] = {key: value[i] for key, value in doc["data"].items()}
                sleep(self.delay)
                super().event(new_event)
                


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main():

    # if bool(os.environ["DEBUG"]):
    if str(os.environ["DEBUG"]).lower() == "true":
        logger.setLevel(logging.DEBUG)
    
    debug_is_enabled = logger.isEnabledFor(logging.DEBUG)

    # print(f'{os.environ["DEBUG"]=}')
    # print(f'{bool(os.environ["DEBUG"])=}')
    # print(f'{debug_is_enabled=}')
    
    primary_catalog = catalog[catalog_name]

    selected_runs = primary_catalog
    if debug_is_enabled: 
        logging.debug(f"list(selected_runs): {list(selected_runs)}")
        logging.debug(f"len(selected_runs): {len(selected_runs)}")
    if not list(selected_runs):
        raise Exception(f"Catalog <{catalog_name}> is empty!")

    # Find runs that were generated by a flying scan
    selected_runs = selected_runs.search({"scan_type": "flying"})
    # selected_runs = selected_runs.search({"plan_name": "count"})
    if debug_is_enabled: 
        logging.debug(f"list(selected_runs): {list(selected_runs)}")
        logging.debug(f"len(selected_runs): {len(selected_runs)}")
    if not list(selected_runs):
        raise Exception(f"No flying scans were found")

    selected_runs = selected_runs.search({
        "uid": list(selected_runs)[-1]})
    if debug_is_enabled: 
        logging.debug(f"selected_runs: {list(selected_runs)}")

    for (uid, run) in selected_runs.items():
        if debug_is_enabled: 
            logging.debug(f"run.primary: {run.primary}")
    
        # print(f"{uid=}")
        # print(f"{run.__dict__=}")
        # print(f"{json.dumps(run.metadata)=}")
        print("run.metadata ...")
        pprint(run.metadata)

        # send_to_api = ApiCallback()
        # send_to_api = ApiDelayedCallback(port=8003, delay=0.05)
        send_to_api = ApiDelayedCallback(port=8003, delay=0.1)
        for doc_name, doc in run.documents(fill='no'):
            print(doc_name)
            send_to_api(doc_name, doc)
    
    return(0)

    # Find runs that match requested data file numbers
    scan_nums = args.scan_nums
    if scan_nums:
        selected_runs = selected_runs.search(
            {"scan_number": {"$in": scan_nums}})
    else:
        # Need to return a catalog, not a run or list of runs
        # selected_runs = [selected_runs[-1]] # return a list
        # selected_runs = selected_runs[list(selected_runs)[-1]]
        selected_runs = selected_runs.search({
            "uid": list(selected_runs)[-1]})
        if debug_is_enabled: 
            logging.debug(f"selected_runs: {selected_runs}")
    if debug_is_enabled: 
        logging.debug(f"list(selected_runs): {list(selected_runs)}")
        logging.debug(f"len(selected_runs): {len(selected_runs)}")
    if not list(selected_runs):
        raise Exception(
            f"Catalog <{catalog_name}> has no runs with scan#: {scan_nums}")

    selected_runs_datasets = list()
    

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
if __name__ == '__main__':
    main()
