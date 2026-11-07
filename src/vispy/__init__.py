# -*- coding: utf-8 -*-
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

"""=====
Vispy
=====

This VisPy 0.17.0 compatibility fork renders through Dawn, using Vulkan on
Windows/Linux and Metal on macOS. Familiar application, gloo, visual and scene
interfaces support the workflows described in the fork's compatibility docs.
Those docs define the supported values, platform profiles and remaining gaps;
macOS graphics support is experimental.

The fork README describes current support. Upstream API documentation is at
http://vispy.org.
"""

from __future__ import division

__all__ = ['use', 'sys_info', 'set_log_level', 'test']

try:
    from .version import version as __version__  # noqa
except ImportError:
    # package is not installed
    pass

from .util import config, set_log_level, keys, sys_info  # noqa
from .util.wrappers import use, test  # noqa


def _get_sg_image_scraper():
    from .util.gallery_scraper import VisPyGalleryScraper
    return VisPyGalleryScraper()
