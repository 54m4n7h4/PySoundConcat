from __future__ import print_function
import os
import numpy as np
import logging
import pdb

from fileops import pathops

logger = logging.getLogger(__name__)

class Analysis(object):

    """
    Basic descriptor class to build analyses on.

    The Analysis base class works as an interface between child descriptor
    objects and the HDF5 storage file. This is designed to seperate descriptor
    generation from data IO, allowing for quick development of new descriptor
    classes.  The base Analysis class has methods for retreiving analyses from
    file and saving data created by analysis objects to file. It also has basic
    formatting methods used to return data in the required format for processed
    such as descriptor comparisons.

    In order to create a new descriptor, the hdf5_dataset_formatter method will
    need to be overwritten by the child class to generate and store the
    descriptor's output in the appropriate manner. Examples of this can be seen
    through the currently implemented descriptors.
    """

    def __init__(self, AnalysedAudioFile, frames, analysis_group, name, config=None):
        # Create object logger
        self.logger = logging.getLogger(__name__ + '.{0}Analysis'.format(name))
        # Store AnalysedAudioFile object to be analysed.
        self.AnalysedAudioFile = AnalysedAudioFile
        self.analysis_group = analysis_group
        self.name = name

    def create_analysis(self, *args, **kwargs):
        """
        Create the analysis and save to the HDF5 file.

        analysis_function: The function used to create the analysis. returned
        data will be stored in the HDF5 file.
        """

        try:
            self.analysis = self.analysis_group.create_group(self.name)
        except ValueError:
            self.logger.info("{0} analysis group already exists".format(self.name))
            self.analysis = self.analysis_group[self.name]

        # If forcing new analysis creation then delete old analysis and create
        # a new one
        if self.AnalysedAudioFile.force_analysis:
            self.logger.info("Force re-analysis is enabled. "
                                "deleting: {0}".format(self.analysis.name))
            # Delete all pre-existing data in database.
            for i in self.analysis.iterkeys():
                del self.analysis[i]
            # Run the analysis function and format it's returned data ready to
            # be saved in the HDF5 file
            data_dict, attrs_dict = self.hdf5_dataset_formatter(*args, **kwargs)
            for key, value in data_dict.iteritems():
                self.analysis.create_dataset(key, data=value, chunks=True)
            for key, value in attrs_dict.iteritems():
                self.analysis.attrs[key] = value
        else:

            if self.analysis.keys():
                self.logger.info("Analysis already exists. Reading from: "
                                 "{0}".format(self.analysis.name))
            else:
                # If it doesn't then generate a new file
                # Run the analysis function and format it's returned data ready to
                # be saved in the HDF5 file
                data_dict, attrs_dict = self.hdf5_dataset_formatter(*args, **kwargs)
                for key, value in data_dict.iteritems():
                    self.analysis.create_dataset(key, data=value, chunks=True)
                for key, value in attrs_dict.iteritems():
                    self.analysis.attrs[key] = value

    def get_analysis_grains(self, start, end):
        """
        Retrieve analysis frames for period specified in start and end times.
        arrays of start and end time pairs will produce an array of equivelant
        size containing frames for these times.
        """
        times = self.analysis_group[self.name]["times"][:]
        start = start / 1000
        end = end / 1000
        vtimes = times.reshape(-1, 1)

        selection = np.transpose((vtimes >= start) & (vtimes <= end))
        # If there are no frames for this grain, take the two closest frames
        # from the adjacent grains.
        if not selection.any():
            frame_center = start + (end-start)/2.
            closest_frames = np.abs(vtimes-frame_center).argsort()[:2]
            selection[closest_frames] = True

        #start_ind = np.min(selection)
        #end_ind = np.argmax(selection)
        frames = self.analysis_group[self.name]["frames"][:]

        grain_data = (frames, selection)

        return grain_data

    def hdf5_dataset_formatter(analysis_method, *args, **kwargs):
        '''
        Note: This is a generic formatter designed as a template to be
        overwritten by a descriptor sub-class.

        Formats the output from the analysis method to save to the HDF5 file.

        Places data and attributes in 2 dictionaries to be stored in the HDF5
        file.
        '''
        output, attributes = analysis_method(*args, **kwargs)
        return ({'data': output}, {'attrs': attributes})

    ################################################################################
    # Formatting functions
    ################################################################################

    def log2_median(self, x):
        return np.median(1000 * np.log2(1+x/1000))

    def log2_mean(self, x):
        return np.mean(1000 * np.log2(1+x/1000))

    def formatter_func(self, selection, frames, valid_inds, formatter=None):
        # get all valid frames from current grain
        frames = frames[selection & valid_inds]

        return formatter(frames)
        #if less than half the frames are valid then the grain is not valid.
        if frames.size < valid_inds[selection].nonzero()[0].size/2:
            return np.nan

    def analysis_formatter(self, frames, selection, format):
        """Calculate the average analysis value of the grain using the match format specified."""
        valid_inds = np.isfinite(frames)

        format_style_dict = {
            'mean': np.mean,
            'median': np.median,
            'log2_mean': self.log2_mean,
            'log2_median': self.log2_median,
        }
        output = np.empty(len(selection))

        if not selection.size:
            # TODO: Add warning here
            return np.nan
        # For debugging apply_along_axis:
        #for ind, i in enumerate(selection):
        #    output[ind] = self.formatter_func(i, frames, valid_inds, formatter=format_style_dict[format])

        output = np.apply_along_axis(self.formatter_func, 1, selection, frames, valid_inds, formatter=format_style_dict[format])
        return output
