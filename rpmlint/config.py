from glob import glob
from importlib.util import find_spec
import os
from pprint import pprint
import re

from configobj import ConfigObj
from rpmlint.configdefaults import DEFAULTS, DICT_DEFAULTS
from rpmlint.helpers import print_warning
# This is shipped by ConfigObj upstream
from validate import Validator
from xdg.BaseDirectory import xdg_config_dirs


class Config(object):
    """
    Class wrapping testing loading and parsing.
    By default it loads all default locations and initializes basic testing
    layout for the rpmlint binary.
    Based on the opening order 'newer' configuration takes precedence over
    already existing one.
    """

    re_filter = re.compile(r'\s*addFilter\([\"\'](.*)[\"\']\)')
    re_badness = re.compile(r'\s*setBadness\([\'\"](.*)[\'\"],\s*[\'\"]?(\d+)[\'\"]?\)')
    # config elements that are known lists and append to each other
    known_lists_merged = (
        'Filters',
        'Checks',
    )
    # config elements that are known lists and override each other
    known_lists_override = (
        'ExtraMenuNeeds',
        'ValidMenuSections',
        'InvalidRequires',
        'DisallowedDirs',
        'StandardGroups',
        'StandardUsers',
        'SystemLibPaths',
        'ValidEmptyShells',
        'ValidGroups',
        'ValidLicenses',
        'ValidShells',
    )
    # filename with configuration specifications
    __configspecfilename = os.path.join(os.path.dirname(__file__), 'configspec.cfg')

    def __init__(self, config=None):
        # ordered list of configuration files we loaded
        # usefull when debugging where from we got all the config options
        self.conf_files = list()
        # Configuration content parsed from the ini file
        self.configuration = None
        # wether to print more informations or not
        self.info = False
        self.find_configs(config)
        for config in self.conf_files:
            self.load_config(config)
        if not self.configuration:
            # now in a case there is nada wrt configurations
            self.load_config('nill-temporary')

    def reset_checks(self):
        """
        Remove all planned checks from the loaded config.
        """
        self.configuration['Checks'] = list()

    def add_check(self, check):
        """
        Add specified file to be loaded up by checks.
        Check is just a string file.
        It used to be possible to specify additional locations for checks
        but to keep it simple all checks must be part of rpmlint package
         -> from rpmlint.checks.<CHECKNAME> import *
        """
        # Validate first if it is possible to import the added check
        if find_spec('.{}'.format(check), package='rpmlint.checks'):
            self.configuration['Checks'].append(check)
        else:
            print_warning('(none): W: error adding requested check: {}'.format(check))

    def set_badness(self, result, badness):
        """
        Set specific badness for some result
        """
        self.configuration['Scoring'][result] = badness

    def find_configs(self, config=None):
        """
        Load all the configuration files from XDG_CONFIG_DIRS.
        User can override and then only his config is loaded.
        """

        if config:
            if os.path.exists(config):
                # load this only if it really exist
                self.conf_files = [config]
                return
            else:
                print_warning('(none): W: error locating user requested configuration: {}'.format(config))

        for directory in reversed(xdg_config_dirs):
            confdir = os.path.join(directory, 'rpmlint')
            if os.path.isdir(confdir):
                # load all configs in the folders
                confopts = glob('{}/*config'.format(confdir))
                confopts.sort()
                self.conf_files += confopts

    def print_config(self):
        """
        Just pretty print the current state of the config
        """
        if self.configuration:
            pprint(self.configuration)

    def load_config(self, config):
        """
        Load the configuration file and append it to local dictionary with the
        content of already loaded options.
        """
        if config not in self.conf_files:
            # just add the config for tracking purposes, someone injected
            # config file to us
            self.conf_files.append(config)

        # load and validate initial config
        val = Validator()
        configspec = ConfigObj(self.__configspecfilename, _inspec=True)
        cfg = ConfigObj(config, configspec=configspec)
        if not cfg.validate(val):
            print_warning('(none): W: error parsing configuration file: {}'.format(config))
        # load multiline defaults
        cfg = self._load_defaults(cfg, DEFAULTS)
        cfg = self._load_defaults(cfg, DICT_DEFAULTS)
        # convert all list items to real lists
        cfg = self._convert_known_lists(cfg, self.known_lists_merged)
        cfg = self._convert_known_lists(cfg, self.known_lists_override, True)
        # for merging we have duplicate object without filled in defaults
        result = ConfigObj(config)
        # conver the result stuff to lists too
        result = self._convert_known_lists(result, self.known_lists_merged)
        result = self._convert_known_lists(result, self.known_lists_override, True)
        # merge the dict on where we are merging lists
        for i in self.known_lists_merged:
            if self.configuration:
                if i in self.configuration and i in result:
                    result[i] = result[i] + self.configuration[i]

        # Merge stuff in a case we alrady have config
        if self.configuration:
            self.configuration.merge(result)
        else:
            self.configuration = cfg

    def _load_defaults(self, config, keywords):
        """
        In case of multiline/dictionary defaults specified in configspec the
        configobj crashes.
        As such we have all the content strings stored in separate class
        where we will assign them to here.
        """
        for keyword in keywords:
            # store only in a case there is already not some user value
            if not config[keyword]:
                config[keyword] = keywords[keyword]
        return config

    def _convert_known_lists(self, config, keywords, tuplify=False):
        """
        Convert known mutliline strings to known lists, as the ConfigObj parser
        really sucks at parsing multiline lists.
        We also ommit all the whitespace around the elements to avoid random
        copy&pastos
        If we specify tuplify argument we rather return tuple over list
        """
        for keyword in keywords:
            if keyword in config:
                config[keyword] = \
                    ([s.strip() for s in config[keyword].strip().splitlines() if s.strip() and not s.lstrip().startswith('#')])
                if tuplify:
                    config[keyword] = tuple(config[keyword])
        return config

    def load_rpmlintrc(self, rpmlint_file):
        """
        Function to load up existing rpmlintrc files
        Only setBadness and addFilter are processed
        """
        if not self.configuration:
            print_warning('(none): W: loading rpmlint before configuration is not allowed: {}'.format(rpmlint_file))
            return
        with open(rpmlint_file) as f:
            rpmlintrc_content = f.read()
        filters = self.re_filter.findall(rpmlintrc_content)
        self.configuration['Filters'] += filters
        badness = self.re_badness.findall(rpmlintrc_content)
        for entry in badness:
            self.configuration['Scoring'].update({entry[0]: entry[1]})
