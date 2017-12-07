"""
This module contains all available rpc commands.
"""

import asyncio
import uptime


def uptime():
    """
    RPC command which returns the current uptime of
    this client.

    Returns
    -------
        uptime
    """
    return uptime.uptime()
