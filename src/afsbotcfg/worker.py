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

from twisted.python import log

from buildbot.worker.local import LocalWorker


def canStartBuild(builder, workerforbuilder, buildrequest):
    workername = workerforbuilder.worker.workername

    # Enforce selected worker if choosen in force build form.
    if 'workername' in buildrequest.properties:
        chosen = buildrequest.properties['workername']
        if isinstance(chosen, str) and chosen == workername:
            return True

    # The dummy worker is a fallback to skip builds when no real workers
    # are attached. The builder.workers list contains all of the currently
    # attached workers, including workers that are busy doing a build.
    if workername == 'dummy':
        attached_real_workers = []
        for wfb in builder.workers:
            if wfb.worker.workername != 'dummy':
                attached_real_workers.append(wfb.worker.workername)
        if len(attached_real_workers) == 0:
            log.msg(f"afsbotcfg: canStartBuild: no real workers found, skipping build {buildrequest.id}")
            return True
        return False

    # Proceed with real worker.
    return True


class DummyWorker(LocalWorker):
    """
    A local stand-in worker to be used to skip builds when no
    others workers are attached to a builder.  The build steps
    must be configured to be skipped when the current worker
    is a dummy worker.
    """
    def __init__(self, name="dummy", **kwargs):
        super().__init__(name, **kwargs)
