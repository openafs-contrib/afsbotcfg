# Copyright (c) 2025 Sine Nomine Associates
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

from buildbot.worker.local import LocalWorker


class DummyWorker(LocalWorker):
    """
    A local stand-in worker to be used to skip builds when no
    others workers are attached to a builder.  The build steps
    must be configured to be skipped when the current worker
    is a dummy worker.
    """
    def __init__(self, name="dummy", **kwargs):
        super().__init__(name, **kwargs)
