# SPDX-License-Identifier: AGPL-3.0-only
"""Exact final-verdict contract for the scoped scientific peer-review record."""


def require_ready_review(response,expected):
    if type(response) is not dict or response.get('is_error') is not False:
        raise ValueError('Successful peer-review envelope required')
    result=response.get('result')
    if type(result) is not str or not result.strip():
        raise ValueError('Peer-review text required')
    if 'FIX_BEFORE_CAPTURE' in result or result.rstrip().splitlines()[-1]!=expected:
        raise ValueError('Exact final ready verdict without a fix verdict required')
