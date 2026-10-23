# SPDX-License-Identifier: AGPL-3.0-only
"""Geometry exclusion for future, not-yet-generated smooth-line holdouts.

The registry contains training geometry hashes only. Constructing or querying it
never reads a held-out descriptor or frame. Endpoint reversal is excluded too.
"""
import hashlib
import json

try:
    from .smooth_line_mechanism import Probe
except ImportError:
    from smooth_line_mechanism import Probe


def geometry_digest(probe):
    if (type(probe) is not Probe or type(probe.width_units) is not int or probe.width_units <= 0 or
            any(type(point) not in (tuple,list) or len(point) != 2 or
                any(type(value) is not int for value in point)
                for point in (probe.start_units,probe.end_units))):
        raise ValueError('Exact integer segment geometry required')
    endpoints=sorted((list(probe.start_units),list(probe.end_units)))
    body=json.dumps([endpoints,probe.width_units],separators=(',',':')).encode('ascii')
    return hashlib.sha256(body).hexdigest()


def training_exclusion(probes):
    return frozenset(geometry_digest(probe) for probe in probes)


def require_unseen_geometry(probe,excluded):
    if geometry_digest(probe) in excluded:
        raise ValueError('Future holdout geometry duplicates training, including endpoint reversal')
