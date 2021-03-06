#!/usr/bin/env python
# This python program logs detected events, within the
# Gnuradio Companion environment
# -*- coding: utf-8 -*-
#
# Copyright 2018 Glen Langston, Quiet Skies <+YOU OR YOUR COMPANY+>.
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# HISTORY
# 20JUN26 GIL log vector tags to deterine accurate time
# 19FEB14 GIL make tag labels compatible with C++ tags
# 19JAN19 GIL initial version based on ra_event_sink

import os
import sys
import datetime
import numpy as np
from gnuradio import gr
import pmt

class ra_event_log(gr.sync_block):
    """
    Event Log writes a summary of detected events to a log file.  The input
    1) vector of I,Q (complex) samples centered in time on the event
    The Event MJD, Peak and RMS are passed as tags
    Parameters are
    1) LogFileName
    2) Note on Purpose of event detection
    2) Vector length in Channels
    3) Bandwidth (Hz)
    This block is intended to reduce the downstream CPU load.
    """
    def __init__(self, logname, note, vlen, bandwidth):
        gr.sync_block.__init__(self,
                               name="ra_event_log",              
                               # inputs: 
                               # peak, rms, Event MJD
                               in_sig=[(np.complex64, int(vlen))],
                               # no outputs
                               out_sig=None, )
        vlen = int(vlen)
        self.vlen = vlen
        self.ecount = 0
        self.lastmjd = 0.
        self.lastvmjd = 0.
        self.printmjd = 0.
        self.bandwidth = bandwidth
        now = datetime.datetime.utcnow()
        self.startutc = now
        self.setupdir = "./"
        self.logname = str(logname)
        self.emjd = 0.
        self.epeak = 0.
        self.erms = 0.
        self.evector = 0L
        self.env = 0L
        self.eoffset = 0
        self.voffset = 0
        self.vmjd = 0.
        self.vcount = 0L
        self.nv = 0L
        self.lasttag = ""
        self.note = str(note)
        self.pformat = "%18.12f %15d %05d %10.3f %3d %5d %10.6f %10.6f %5d %5d\n" 
        self.vformat = "%18.12f %15d %05d %10.3f %3d %5d \n" 
        self.set_note( note)          # should set all values before opening log file
        self.set_sample_rate( bandwidth)
        self.set_logname(logname)
        
    def forecast(self, noutput_items, ninput_items): #forcast is a no op
        """
        The work block always processes all inputs
        """
        ninput_items = noutput_items
        return ninput_items

    def set_vlen(self, vlen):
        """
        Save vector length
        """
        self.vlen = int(vlen)

    def set_sample_rate(self, bandwidth):
        """
        Set the sample rate to know the time resolution
        """
        bandwidth = np.float(bandwidth)
        if bandwidth == 0:
            print("Invalid Bandwidth: ", bandwidth)
            return
        self.bandwidth = bandwidth
        print("Setting Bandwidth: %10.6f MHz" % (self.bandwidth))

    def get_sample_rate(self):
        """
        Return the sample rate to know the time resolution
        """
        return self.bandwidth

    def get_event_count(self):
        """
        Return the count of events so far logged
        """
        return self.ecount

    def set_logname(self, logname):
        """
        Read the setup files and initialize all values
        """
        logname = str(logname)
        if len(logname) < 1:   # if no log file name provided
            strnow = self.startutc.isoformat()
            datestr = strnow.split('.')  # get rid of fractions of a second
            daypart = datestr[0]         
            yymmdd = daypart[2:19]       # 2019-01-19T01:23:45 -> 19-01-19T01:23:45
            yymmdd = yymmdd.replace(":", "")  # -> 19-01-19T012345

            logname = "Event-%s.log" % (yymmdd)  # create from date
        self.logname = logname

        with open( self.logname, "w") as f:
            outline = "# Event Log Opened on %s\n" % (self.startutc.isoformat())
            f.write(outline)
            outline = "# %s\n" % (self.note)
            f.write(outline)
            outline = "# bandwidth = %15.6f MHz\n" % (self.bandwidth)
            f.write(outline)
            outline = "# vlen      = %6d\n" % (self.vlen)
            f.write(outline)
            outline = "#E       MJD           vector #   second  micro.sec  NV  Zero#   Peak       RMS    Event# Offset\n"
            f.write(outline)
            outline = "#V       MJD           vector #   second  micro.sec  NV  Zero#\n"
            f.write(outline)
            f.close()

        return
    
    def set_note(self, note):
        """
        Update the note for the event log
        """
        self.note = str(note)
        return

    def work(self, input_items, output_items):
        """
        Work averages all input vectors and outputs one vector for each N inputs
        """
        inn = input_items[0]    # vectors of I/Q (complex) samples
        
        # get the number of input vectors
        nv = len(inn)           # number of events in this port
        
        # get any tags of a new detected event
#        tags = self.get_tags_in_window(0, 0, +self.vlen, pmt.to_pmt('event'))
        tags = self.get_tags_in_window(0, 0, +nv)
        # if there are tags, then a new event was detected
        if len(tags) > 0:
            for tag in tags:
#                print 'Tag: ', tag
                key = pmt.to_python(tag.key)
                value = pmt.to_python(tag.value)
                if key == 'MJD':
                    self.emjd = value
#                    print 'Tag MJD : %15.9f' % (self.emjd)
                elif key == 'VMJD':
                    self.vmjd = value
                    # print 'Tag VMJD: %15.9f' % (self.vmjd)
                elif key == 'PEAK':
                    self.epeak = value
#                    print 'Tag PEAK: %7.4f' % (self.epeak)
                elif key == 'RMS':
                    self.erms = value
#                    print 'Tag RMs : %7.4f' % (self.erms)
                elif key == 'VCOUNT':
                    self.vcount = value
                    # print 'Tag VCOUNT: %15.9f' % (self.vcount)
                elif key == 'EVECTOR':
                    self.evector = value
                    # print 'Tag VMJD: %15.9f' % (self.emjd)
                elif key == 'ENV':
                    self.env = value
                elif key == 'EOFFSET':
                    self.eoffset = value
                elif key == 'VOFFSET':
                    self.voffset = value
                elif key == 'NV':
                    self.nv = value
                    # print 'Tag NV  : %15d' % (self.nv)
                elif key != self.lasttag:
                    print('Unknown Tag: ', key, value)
                    self.lasttag = key

        i = nv - 1
        # expect only one event in tag group
        if i > -1:
            # if a new Modified Julian Day, then an event was detected
            if self.emjd > self.lastmjd:
                # log the event
                self.ecount = self.ecount + 1
                print("Event : %15.9f %16d %9.4f %8.4f %4d" % (self.emjd, self.evector, self.epeak, self.erms, self.ecount))
                imjd = np.int(self.emjd)
                seconds = (self.emjd - imjd)*86400.
                isecond = np.int(seconds)
                microseconds = (seconds - isecond) * 1.e6
                self.lastmjd = self.emjd
                outline = self.pformat % (self.emjd, self.evector, isecond, microseconds, self.env, self.voffset, self.epeak, self.erms, self.ecount, self.eoffset)
                try:
                    with open( self.logname, "a+") as f:
                        f.write(outline)
                        f.close()
                except:
                    print("Can Not Log")
                
            # also log vector time tags to interpolate accurate time
            if self.vmjd > self.lastvmjd:
                # log the time of this vector
                if self.vmjd > self.printmjd:
                    print("Vector: %15.9f %16d %4d %5d" % (self.vmjd, self.vcount, self.nv, self.voffset))
                    # print every minute (24*60 = 1440 minutes in a day)
                    self.printmjd = self.vmjd + (1./1440.)   
                imjd = np.int(self.vmjd)
                seconds = (self.vmjd - imjd)*86400.
                isecond = np.int(seconds)
                microseconds = (seconds - isecond) * 1.e6
                self.lastvmjd = self.vmjd
                outline = self.vformat % (self.vmjd, self.vcount, isecond, microseconds, self.nv, self.voffset)
                try:
                    with open( self.logname, "a+") as f:
                        f.write(outline)
                        f.close()
                except:
                    print("Can Not Log")
                
            # end for all input events
        return nv
    # end event_log()


