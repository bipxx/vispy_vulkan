# SPDX-License-Identifier: AGPL-3.0-only
"""Queue lifetime controls without a native module or device."""
import gc
import weakref

from vispy.gloo.glir import GlirQueue
from vispy.gloo.globject import GLObject


class Parser:
    def __init__(self):
        self.batches = []
        self.retired = []

    def parse(self, commands):
        self.batches.append(commands)

    def retire_orphaned(self, ids):
        self.retired.extend(ids)


def test_orphan_retires_deletes_once_without_replaying_other_commands():
    parser = Parser()
    queue = GlirQueue()
    queue.flush(parser)
    queue.command('FUNC', 'glClear', 0x4000)
    queue.command('DELETE', 17)
    shared = weakref.ref(queue._shared)
    del queue
    gc.collect()
    assert shared() is None
    assert parser.retired == [17]
    assert parser.batches == [[]]


def test_delete_after_queue_finalization_retires_immediately():
    parser = Parser()
    queue = GlirQueue()
    queue.flush(parser)
    shared = queue._shared
    shared.__del__()
    shared.command('FUNC', 'glClear', 0x4000)
    shared.command('DELETE', 18)
    shared.__del__()
    assert parser.retired == [18]
    assert shared.clear() == []


def test_live_alias_keeps_pending_deletion_ordered_until_flush():
    parser = Parser()
    queue, peer = GlirQueue(), GlirQueue()
    queue.associate(peer)
    queue.flush(parser)
    queue.command('DRAW', 1, 'triangles', (0, 3), 1)
    queue.command('DELETE', 1)
    del queue
    gc.collect()
    assert parser.retired == []
    peer.flush(parser)
    assert [c[0] for c in parser.batches[-1]] == ['DRAW', 'DELETE']
    del peer
    gc.collect()
    assert parser.retired == []


def test_merge_transfers_retirement_hook_from_previously_flushed_queue():
    parser = Parser()
    destination, source = GlirQueue(), GlirQueue()
    source.flush(parser)
    source.command('DELETE', 19)
    destination.associate(source)
    del source
    gc.collect()
    assert parser.retired == []
    del destination
    gc.collect()
    assert parser.retired == [19]


def test_unflushed_queue_and_parser_without_hook_need_no_native_retirement():
    class LocalParser:
        def parse(self, commands):
            pass

    queue = GlirQueue()
    queue.command('DELETE', 20)
    del queue
    queue = GlirQueue()
    queue.flush(LocalParser())
    queue.command('DELETE', 21)
    del queue
    gc.collect()


def test_unreachable_object_cycle_handles_queue_before_object_finalization():
    class Owner:
        pass

    parser = Parser()
    owner = Owner()
    owner.queue = GlirQueue()  # shared queue precedes GLObject in the GC graph
    owner.object = GLObject()
    object_id = owner.object.id
    owner.object.owner = owner
    owner.queue.associate(owner.object.glir)
    owner.queue.flush(parser)
    queue_ref, object_ref = weakref.ref(owner.queue), weakref.ref(owner.object)
    del owner
    gc.collect()
    assert queue_ref() is object_ref() is None
    assert parser.retired == [object_id]
