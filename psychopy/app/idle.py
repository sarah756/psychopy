#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2018 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

from __future__ import absolute_import, division, print_function

import threading
import time
from collections import OrderedDict

import wx

from psychopy import prefs, logging
from psychopy.constants import NOT_STARTED, STARTED, SKIP, FINISHED
from . import connections
from psychopy.tools import versionchooser as vc

_t0 = time.time()


def checkFFMPEG(app=None):
    """Helper function for checking imageio ffmpeg support"""
    try:
        import imageio
        haveImageio = True
    except ImportError:
        haveImageio = False

    if haveImageio:
        # Use pre-installed ffmpeg if available.
        # Otherwise, download ffmpeg binary.
        try:
            imageio.plugins.ffmpeg.get_exe()
        except imageio.core.NeedDownloadError:
            imageio.plugins.ffmpeg.download()


tasks = OrderedDict()
if prefs.connections['allowUsageStats']:
    tasks['sendUsageStats'] = {
        'status': NOT_STARTED,
        'func': connections.sendUsageStats,
        'tstart': None, 'tEnd': None,
    }
else:
    tasks['sendUsageStats'] = {
        'status': SKIP,
        'func': connections.sendUsageStats,
        'tstart': None, 'tEnd': None,
    }
if prefs.connections['checkForUpdates']:
    tasks['checkForUpdates'] = {
        'status': SKIP,
        'func': connections.getLatestVersionInfo,
        'tstart': None, 'tEnd': None,
    }
else:
    tasks['checkForUpdates'] = {
        'status': SKIP,
        'func': connections.getLatestVersionInfo,
        'tstart': None, 'tEnd': None,
    }

tasks['checkNews'] = {
    'status': NOT_STARTED,
    'func': connections.getNewsItems,
    'tstart': None, 'tEnd': None,
}
tasks['showTips'] = {
    'status': NOT_STARTED,
    'func': None,
    'tstart': None, 'tEnd': None,
}
tasks['checkFFMPG'] = {
    'status': NOT_STARTED,
    'func': checkFFMPEG,
    'tstart': None, 'tEnd': None,
}
tasks['updateVersionChooser'] = {
    'status': NOT_STARTED,
    'func': vc._remoteVersions,
    'tstart': None, 'tEnd': None,
}

currentTask = None


def doIdleTasks(app=None):
    global currentTask

    if currentTask and currentTask['thread'].is_alive():
        return 0

    for taskName in tasks:
        thisTask = tasks[taskName]
        thisStatus = tasks[taskName]['status']
        if thisStatus == NOT_STARTED:
            currentTask = thisTask
            currentTask['tStart'] = time.time() - _t0
            currentTask['status'] = STARTED
            logging.info('finished {} at {}'.format(taskName,
                                                    currentTask['tStart']))
            _doTask(taskName, app)
            return 0  # something is in motion
        elif thisStatus == STARTED:
            if not currentTask['thread'].is_alive():
                # task finished so take note and pick another
                currentTask['status'] = FINISHED
                currentTask['thread'] = None
                currentTask['tEnd'] = time.time() - _t0
                logging.info('finished {} at {}'.format(taskName,
                                                        currentTask['tEnd']))
                currentTask = None
                continue
            else:
                return 0

    return 1


def _doTask(taskName, app):
    currentTask = tasks[taskName]

    # what args are needed
    if taskName == 'updateVersionChooser':
        args = (True,)
    else:
        args = (app,)

    currentTask['thread'] = threading.Thread(
            target=currentTask['func'], args=args)
    # currentTask['thread'].daemon = True  # kill if the app quits
    currentTask['thread'].start()
