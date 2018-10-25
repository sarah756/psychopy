#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Part of the PsychoPy library
# Copyright (C) 2018 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

from collections import deque
import os
import psychopy
from psychopy.visual.basevisual import (BaseVisualStim,
                                        ContainerMixin,
                                        ColorMixin)
from pandas import read_csv, read_excel


__author__ = 'Jon Peirce, David Bridges, Anthony Haffey'


class Form(BaseVisualStim, ContainerMixin, ColorMixin):
    """A class to add Forms to a `psycopy.visual.Window`

    The Form allows Psychopy to be used as a questionnaire tool, where
    participants can be presented with a series of questions requiring responses.
    Form items, defined as questions and response pairs, are presented
    simultaneously onscreen with a scrollable viewing window.

    Example
    -------
    survey = Form(win, items=[{}], size=(1.0, 0.7), pos=(0.0, 0.0))

    Parameters
    ----------
    win : psychopy.visual.Window
        The window object to present the form.
    items : List of dicts or csv file
        a list of dicts or csv file should have the following key, value pairs / column headers:
                 "questionText": item question string,
                 "questionWidth": question width between 0:1
                 "type": type of rating e.g., 'choice', 'rating', 'slider'
                 "responseWidth": question width between 0:1,
                 "options": list of tick labels for options,
                 "layout": Response object layout e.g., 'horiz' or 'vert'
    textHeight : float
        Text height.
    size : tuple, list
        Size of form on screen.
    pos : tuple, list
        Position of form on screen.
    itemPadding : float
        Space or padding between form items.
    units : str
        units for stimuli - Currently, Form class only operates with 'height' units.
    """

    def __init__(self,
                 win,
                 name='default',
                 items=None,
                 textHeight=.03,
                 size=(.5, .5),
                 pos=(0, 0),
                 itemPadding=0.05,
                 units='height',
                 autoLog=True,
                 ):

        super(Form, self).__init__(win, units, autoLog=False)
        self.win = win
        self.autoLog = autoLog
        self.name = name
        self.items = self.importItems(items)
        self.size = size
        self.pos = pos
        self.itemPadding = itemPadding
        self.scrollSpeed = len(self.items)
        self.units = units

        self.labelHeight = 0.02
        self.textHeight = textHeight
        self._items = {'question': [], 'response': []}
        self._baseYpositions = []
        self.leftEdge = None
        self.rightEdge = None
        self.topEdge = None
        self.virtualHeight = 0  # Virtual height determines pos from boundary box
        self._scrollOffset = 0
        # Create layout of form
        self._doLayout()

        if self.autoLog:
            psychopy.logging.exp("Created {} = {}".format(self.name, repr(self)))

    def __repr__(self, complete=False):
        return self.__str__(complete=complete)  # from MinimalStim

    def importItems(self, items):
        """Import items from csv or excel sheet and convert to list of dicts.
        Will also accept a list of dicts.

        Note, for csv and excel files, 'options' must contain comma separated values,
        e.g., one, two, three. No parenthesis, or quotation marks required.

        Returns
        -------
        List of dicts
            A list of dicts, where each list entry is a dict containing all fields for a single Form item
        """

        def _checkOptions(options):
            """A nested function for testing the number of options given

            Raises ValueError if n Options not > 1
            """
            if not len(options) > 1:
                msg = "Provide at least two possible options for your item responses."
                if self.autoLog:
                    psychopy.logging.error(msg)
                raise ValueError(msg)

        def _checkHeaders(fields):
            """A nested function for testing the names of fields in any given set of items

            Raises NameError if fields do not match required survey fields
            """
            surveyFields = ['responseWidth', 'layout', 'questionText', 'type', 'questionWidth', 'options']
            if not set(surveyFields) == set(fields):
                msg = "Use the following fields/column names for Forms...\n{}".format(surveyFields)
                if self.autoLog:
                    psychopy.logging.error(msg)
                raise NameError(msg)


        # Check for list of dicts that may be passed through Coder
        if isinstance(items, list):  # a list of dicts
            if self.autoLog:
                psychopy.logging.info("Importing items from list...")
            for dicts in items:
                _checkHeaders(dicts.keys())
                _checkOptions(dicts['options'])
            return items
        elif isinstance(items, dict):  # a single entry
            if self.autoLog:
                psychopy.logging.info("Importing items from dict...")
            _checkHeaders(items.keys())
            _checkOptions(items['options'])
            return [items]
        elif os.path.exists(items):
            if self.autoLog:
                psychopy.logging.info("Importing items from file...")
            if '.csv' in items:
                newItems = read_csv(items).dropna()
            elif '.xlsx' in items or '.xls' in items:
                newItems = read_excel(items).dropna()
            else:
                msg = "Form only accepts csv or Excel (.xlsx, .xls) files."
                psychopy.logging.error(msg)
                raise TypeError(msg)
            if self.autoLog:
                psychopy.logging.warn("Dropped rows with NaN values from imported file")
            # Check column headers
            _checkHeaders(list(newItems.columns.values))
            # Convert options to list of strings
            newItems['options'] = newItems['options'].str.split(',')
            # Check that each answer option has more than 1 option
            [_checkOptions(options) for options in newItems['options']]
            # Transpose to list of dicts
            newItems = newItems.T.to_dict().values()
            return newItems
        else:
            msg = "Filename does not exist: '{}'".format(items)
            psychopy.logging.error(msg)
            raise OSError(msg)

    def _setQuestion(self, item):
        """Creates TextStim object containing question

        Returns
        -------
        psychopy.visual.text.TextStim
            The textstim object with the question string
        questionHeight
            The height of the question bounding box as type float
        questionWidth
            The width of the question bounding box as type float
        """
        if self.autoLog:
            psychopy.logging.exp("Question text: {}".format(item['questionText']))

        question = psychopy.visual.TextStim(self.win,
                                   text=item['questionText'],
                                   units=self.units,
                                   height=self.textHeight,
                                   alignHoriz='left',
                                   wrapWidth=item['questionWidth'] * self.size[0],
                                   autoLog=False)

        questionHeight = self.getQuestionHeight(question)
        questionWidth = self.getQuestionWidth(question)
        self._items['question'].append(question)

        return question, questionHeight, questionWidth

    def _setResponse(self, item, question):
        """Creates slider object for responses

        Returns
        -------
        psychopy.visual.slider.Slider
            The Slider object for response
        respHeight
            The height of the response object as type float
        """
        if self.autoLog:
            psychopy.logging.exp("Response type: {}".format(item['type']))
            psychopy.logging.exp("Response layout: {}".format(item['layout']))
            psychopy.logging.exp("Response options: {}".format(item['options']))

        pos = (self.rightEdge - item['responseWidth'] * self.size[0], question.pos[1])
        respHeight = self.getRespHeight(item)

        # Set radio button choice layout
        if item['layout'] == 'horiz':
            respSize = (item['responseWidth'] * self.size[0], 0.03)
        elif item['layout'] == 'vert':
            respSize = (0.03, respHeight)

        if item['type'].lower() in ['rating', 'slider']:
            resp = psychopy.visual.Slider(self.win,
                                 pos=pos,
                                 size=(item['responseWidth'] * self.size[0], 0.03),
                                 ticks=[0, 1],
                                 labels=item['options'],
                                 units=self.units,
                                 labelHeight=self.labelHeight,
                                 flip=True,
                                 autoLog=False)
        elif item['type'].lower() in ['choice']:
            resp = psychopy.visual.Slider(self.win,
                                 pos=pos,
                                 size=respSize,
                                 ticks=None,
                                 labels=item['options'],
                                 units=self.units,
                                 labelHeight=self.textHeight,
                                 style='radio',
                                 flip=True,
                                 autoLog=False)

        self._items['response'].append(resp)
        return resp, respHeight

    def getQuestionHeight(self, question=None):
        """Takes TextStim and calculates height of bounding box

        Returns
        -------
        float
            The height of the question bounding box
        """
        return question.boundingBox[1] / float(self.win.size[1] / 2)

    def getQuestionWidth(self, question=None):
        """Takes TextStim and calculates width of bounding box

        Returns
        -------
        float
            The width of the question bounding box
        """
        return question.boundingBox[0] / float(self.win.size[0] / 2)

    def getRespHeight(self, item):
        """Takes list and calculates height of answer

        Returns
        -------
        float
            The height of the response object
        """

        if item['layout'] == 'vert':
            respHeight = len(item['options']) * self.textHeight
        elif item['layout'] == 'horiz':
            if len(item['options']) <= 3:
                respHeight = self.textHeight
            else:
                words = sorted(item['options'], key=len, reverse=True)
                # height = longest option * text height - size accounting for font case aspect ratio
                respHeight = (self.textHeight * len(words[0])) - (.015 * len(words[0]))
        # TODO: Return size based on response types e.g., textbox
        return respHeight

    def _setScrollBar(self):
        """Creates Slider object for scrollbar

        Returns
        -------
        psychopy.visual.slider.Slider
            The Slider object for scroll bar
        """
        return psychopy.visual.Slider(win=self.win, size=(0.03, self.size[1]),
                                      ticks=[0, 1], style='slider',
                                      pos=(self.rightEdge-.015, self.pos[1]),
                                      autoLog=False)

    def _setBorder(self):
        """Creates border using Rect
        Returns
        -------
        psychopy.visual.Rect
            The border for the survey
        """
        return psychopy.visual.Rect(win=self.win, units=self.units, pos=self.pos,
                                    width=self.size[0], height=self.size[1], autoLog=False)

    def _setAperture(self):
        """Blocks text beyond border using Aperture

        Returns
        -------
        psychopy.visual.Aperture
            The aperture setting viewable area for forms
        """
        return psychopy.visual.Aperture(win=self.win, name='aperture',
                               units=self.units, shape='square',
                               size=self.size, pos=(0, 0),
                               autoLog=False)
    def _getScrollOffet(self):
        """Calculate offset position of items in relation to markerPos

        Returns
        -------
        float
            Offset position of items proportionate to scroll bar
        """
        sizeOffset = (1 - self.scrollbar.markerPos) * (self.size[1]-self.itemPadding)
        maxItemPos = min(self._baseYpositions)
        return (maxItemPos - (self.scrollbar.markerPos * maxItemPos) + sizeOffset)

    def _doLayout(self):
        """Define layout of form"""
        # Define boundaries of form
        if self.autoLog:
            psychopy.logging.info("Setting layout of Form: {}.".format(self.name))

        self.leftEdge = self.pos[0] - self.size[0]/2.0
        self.rightEdge = self.pos[0] + self.size[0]/2.0
        self.topEdge = self.pos[1] + self.size[1]/2.0

        # For each question, create textstim and rating scale
        for item in self.items:
            # set up the question text
            question, questionHeight, questionWidth = self._setQuestion(item)
            # Position text relative to boundaries defined according to position and size
            question.pos = (self.leftEdge,
                            self.topEdge
                            + self.virtualHeight
                            - questionHeight/2 - self.itemPadding)
            response, respHeight, = self._setResponse(item, question)
            # Calculate position of question based on larger questionHeight vs respHeight.
            self._baseYpositions.append(self.virtualHeight
                                        - max(respHeight, questionHeight)  # Positionining based on larger of the two
                                       # + (respHeight/2)            # aligns to center
                                        - self.textHeight)       # Padding for unaccounted marker size in slider height
            # update height ready for next row
            self.virtualHeight -= max(respHeight, questionHeight) + self.itemPadding


        # position a slider on right-hand edge
        self.scrollbar = self._setScrollBar()
        self.scrollbar.markerPos = 1  # Set scrollbar to start position
        self.border = self._setBorder()
        self.aperture = self._setAperture()

        if self.autoLog:
            psychopy.logging.info("Layout set for Form: {}.".format(self.name))

    def _inRange(self, item):
        """Check whether item position falls within border area

        Parameters
        ----------
        item : TextStim, Slider object
            TextStim or Slider item from survey

        Returns
        -------
        bool
            Returns True if item position falls within border area
        """
        upperRange = self.size[1]/2
        lowerRange = -self.size[1]/2
        return (item.pos[1] < upperRange and item.pos[1] > lowerRange)

    def draw(self):
        """Draw items on form within border area"""
        decorations = [self.border]  # add scrollbar if it's needed
        fractionVisible = self.size[1]/(-self.virtualHeight)
        if fractionVisible < 1.0:
            decorations.append(self.scrollbar)

        # Check mouse wheel
        self.scrollbar.markerPos += self.scrollbar.mouse.getWheelRel()[1]/self.scrollSpeed

        # draw the box and scrollbar
        self.aperture.enable()
        for decoration in decorations:
            decoration.draw()

        # draw the items
        for element in self._items.keys():
            for idx, items in enumerate(self._items[element]):
                items.pos = (items.pos[0], self.size[1]/2 + self._baseYpositions[idx] - self._getScrollOffet())
                # Only draw if within border range for efficiency
                if self._inRange(items):
                    items.draw()
        self.aperture.disable()

    def getData(self):
        """Extracts form questions, response ratings and response times from Form items

        Returns
        -------
        dict
            A dictionary storing lists of questions, response ratings and response times
        """
        formData = {'questions': deque([]), 'ratings': deque([]), 'rt': deque([])}
        [formData['questions'].append(element.text) for element in self._items['question']]
        [formData['ratings'].append(element.getRating()) for element in self._items['response']]
        [formData['rt'].append(element.getRT()) for element in self._items['response']]
        return formData

    def formComplete(self):
        """Checks all Form items for a response

        Returns
        -------
        bool
            True if all items contain a response, False otherwise.
        """
        return None not in self.getData()['ratings']