"""Provider-free Windows pacing evidence contracts; every OS/Qt API is a fake."""
import copy
import ctypes
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


SCRIPT = Path(os.environ.get('VISPY_BENCHMARK_SCRIPT',
    str(Path(__file__).resolve().parents[2] / 'tools/benchmark_frames.py')))
SPEC = importlib.util.spec_from_file_location('_point_presentation_pacing_tests', SCRIPT.with_name('benchmark_pacing.py'))
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


@pytest.fixture(autouse=True)
def no_real_native_api(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('CPU pacing test attempted a real DLL or function-pointer binding')
    monkeypatch.setattr(P.ctypes, 'WinDLL', forbidden, raising=False)
    monkeypatch.setattr(P.ctypes, 'WINFUNCTYPE', forbidden, raising=False)


def teardown_module():
    forbidden = [n for n in sys.modules if n == 'vispy' or
                 n.startswith(('vispy.', 'PyQt', 'PySide', 'OpenGL', 'qtpy'))]
    assert not forbidden, 'CPU pacing tests imported a renderer/provider: ' + repr(forbidden)


class NativeDouble:
    def __init__(self, interval=0, extension='ARB'):
        self.interval, self.extension = interval, extension
        self.tuple = dict(hglrc=101, hdc=202, window=303, thread_id=404)
        self.calls = []
        self.on_getter = None

    def snapshot(self):
        self.calls.append(('snapshot',))
        return dict(self.tuple)

    def get_interval(self, hdc):
        self.calls.append(('get_interval', hdc))
        if self.on_getter:
            self.on_getter()
        return self.interval, self.extension


class WindowDouble:
    def __init__(self, thread):
        self.owner_thread, self.hwnd = thread, 303

    def thread(self):
        return self.owner_thread

    def winId(self):
        return self.hwnd


class ContextDouble:
    def __init__(self, surface, thread):
        self.owner_surface, self.owner_thread, self.valid = surface, thread, True
        self.format_interval = 1

    def surface(self):
        return self.owner_surface

    def thread(self):
        return self.owner_thread

    def isValid(self):
        return self.valid

    def format(self):
        # This is intentionally independent of the actual WGL interval.
        return SimpleNamespace(swapInterval=lambda: self.format_interval)


def rig(interval=0, extension='ARB', *, sharing=False, platform='win32'):
    thread = object()
    window = WindowDouble(thread)
    scene = ContextDouble(window, thread)
    current = ContextDouble(window, thread) if sharing else scene
    state = SimpleNamespace(current=current, scene=scene, window=window, thread=thread,
                            current_thread=thread, thread_id=404, sharing=sharing)
    qt_context = SimpleNamespace(currentContext=lambda: state.current,
        areSharing=lambda a, b: state.sharing and {id(a), id(b)} == {id(current), id(scene)})
    qt_thread = SimpleNamespace(currentThread=lambda: state.current_thread,
                               currentThreadId=lambda: state.thread_id)
    widget = SimpleNamespace(context=lambda: state.scene,
        window=lambda: SimpleNamespace(windowHandle=lambda: state.window), thread=lambda: state.thread)
    canvas = SimpleNamespace(native=widget)
    api = NativeDouble(interval, extension)
    constructed = []

    def factory():
        constructed.append(True)
        return api

    observer = P.WindowsPresentationPacing(canvas, qt_context, qt_thread,
        native_factory=factory, platform=platform)
    return observer, state, api, constructed


def observed(frame=7, interval=0):
    observer, state, api, constructed = rig(interval)
    record = observer.observe(frame, closed_frame_id=frame)
    assert record['status'] == 'observed'
    return record


def completed(frame, receipt=None):
    return dict(frame_id=frame, status='success', presented=True,
        scene_and_presentation_syncs_signaled=True,
        presentation_pacing=observed(frame) if receipt is None else receipt)


def test_construction_and_unowned_callbacks_cannot_resolve_native_getter():
    observer, state, api, made = rig()
    assert made == [] and api.calls == [] and observer.native is None
    for frame, owner in ((7, None), (7, 6), (True, True), (7.0, 7)):
        result = observer.observe(frame, closed_frame_id=owner)
        assert result['status'] == 'unproven' and result['interval'] is None and result['errors']
    assert made == [] and api.calls == []
    assert observer.metadata()['pacing_disabled'] is False


@pytest.mark.parametrize('sharing', [False, True])
@pytest.mark.parametrize('extension', ['ARB', 'EXT'])
def test_actual_top_level_current_owner_accepts_same_or_sharing_context(sharing, extension):
    observer, state, api, made = rig(extension=extension, sharing=sharing)
    record = observer.observe(7, closed_frame_id=7)
    assert made == [True]
    assert api.calls == [('snapshot',), ('get_interval', 202), ('snapshot',)]
    assert record['before'] == record['after']
    assert (record['before']['qt_current_context'] != record['before']['qt_scene_context']) is sharing
    assert P.validate_receipt(record, 7, unpaced=True) == 0
    assert observer.metadata()['pacing_disabled'] is True
    assert observer.metadata()['scanout_measured'] is False
    assert observer.metadata()['compositor_throttling_excluded'] is False


@pytest.mark.parametrize('kind', ['no_context','invalid_context','foreign_context','offscreen_surface',
    'callback_thread','widget_thread','context_thread','surface_thread','null_hwnd','bool_hwnd','float_hwnd',
    'bool_thread_id','float_thread_id','missing_top_level'])
def test_qt_ownership_refusal_happens_before_any_native_binding(kind):
    observer, state, api, made = rig(sharing=True)
    if kind == 'no_context': state.current = None
    elif kind == 'invalid_context': state.current.valid = False
    elif kind == 'foreign_context': state.sharing = False
    elif kind == 'offscreen_surface': state.current.owner_surface = object()
    elif kind == 'callback_thread': state.current_thread = object()
    elif kind == 'widget_thread': state.thread = object()
    elif kind == 'context_thread': state.current.owner_thread = object()
    elif kind == 'surface_thread': state.window.owner_thread = object()
    elif kind == 'null_hwnd': state.window.hwnd = 0
    elif kind == 'bool_hwnd': state.window.hwnd = True
    elif kind == 'float_hwnd': state.window.hwnd = 303.0
    elif kind == 'bool_thread_id': state.thread_id = True
    elif kind == 'float_thread_id': state.thread_id = 404.0
    elif kind == 'missing_top_level': state.window = None
    result = observer.observe(7, closed_frame_id=7)
    assert result['status'] == 'unproven' and result['errors'] and result['interval'] is None
    assert made == [] and api.calls == []


@pytest.mark.parametrize('field,value', [('hglrc',0),('hdc',0),('window',999),('thread_id',999),
    ('hglrc',True),('hdc',202.0),('window',None),('thread_id',False)])
def test_native_dc_window_and_thread_tuple_must_match_qt_owner(field, value):
    observer, state, api, made = rig()
    api.tuple[field] = value
    result = observer.observe(7, closed_frame_id=7)
    assert result['status'] == 'unproven' and result['interval'] is None and result['errors']
    assert api.calls == [('snapshot',)]


@pytest.mark.parametrize('field', ['hglrc','hdc','window','thread_id'])
def test_changed_native_tuple_is_never_accepted_even_when_getter_returns_zero(field):
    observer, state, api, made = rig()
    api.on_getter = lambda: api.tuple.__setitem__(field, api.tuple[field]+1)
    result = observer.observe(7, closed_frame_id=7)
    assert result['status'] == 'unproven' and result['interval'] == 0
    assert result['before'] != result['after'] and result['errors']
    with pytest.raises(P.PacingUnavailable):
        P.validate_receipt(result, 7, unpaced=True)


@pytest.mark.parametrize('kind', ['context','surface','thread','hwnd'])
def test_changed_qt_ownership_around_getter_is_retained_not_repaired(kind):
    observer, state, api, made = rig(sharing=True)
    def change():
        if kind == 'context': state.current = state.scene
        elif kind == 'surface': state.current.owner_surface = object()
        elif kind == 'thread': state.current_thread = object()
        else: state.window.hwnd = 304
    api.on_getter = change
    result = observer.observe(7, closed_frame_id=7)
    assert result['status'] == 'unproven' and result['interval'] == 0 and result['errors']
    assert result['before'] != result['after']


@pytest.mark.parametrize('interval', [True,False,0.0,1.0,None,'0',-1])
def test_malformed_or_adaptive_interval_never_becomes_observed_unpaced(interval):
    observer, state, api, made = rig(interval)
    result = observer.observe(7, closed_frame_id=7)
    assert result['status'] == 'unproven' and result['errors']
    assert observer.metadata()['pacing_disabled'] is False


@pytest.mark.parametrize('platform', ['linux','darwin','unknown',None])
def test_unsupported_platform_retains_unknown_without_getter(platform):
    observer, state, api, made = rig(platform=platform)
    if platform is None:
        # The constructor uses the real platform by default, so explicitly
        # exercise an unknown observation instead of relying on the host OS.
        observer.platform = None
    result = observer.observe(7, closed_frame_id=7)
    assert result['status'] == 'unproven' and result['interval'] is None
    assert made == [] and api.calls == []


def test_getter_failure_keeps_after_snapshot_and_original_error():
    observer, state, api, made = rig()
    def fail(): raise RuntimeError('synthetic getter failure')
    api.on_getter = fail
    result = observer.observe(7, closed_frame_id=7)
    assert result['status'] == 'unproven' and result['before'] == result['after']
    assert any('synthetic getter failure' in x for x in result['errors'])
    assert api.calls == [('snapshot',),('get_interval',202),('snapshot',)]


def test_returned_and_sampled_receipts_have_no_nested_alias_to_owner_records():
    observer, state, api, made = rig()
    first = observer.observe(7, closed_frame_id=7)
    pristine = copy.deepcopy(first)
    first['interval'] = 9
    first['before']['native']['window'] = 999
    first['errors'].append('caller mutation')
    copy1 = observer.receipt(7)
    assert copy1 == pristine
    copy1['after']['native']['hdc'] = 123
    assert observer.receipt(7) == pristine
    second = observer.observe(8, closed_frame_id=8)
    second['before']['native']['hglrc'] = 999
    assert observer.receipt(7) == pristine and observer.receipt(8)['before']['native']['hglrc'] == 101
    assert observer.metadata()['pacing_disabled'] is True


def test_duplicate_owner_is_unproven_without_overwriting_original_receipt():
    observer, state, api, made = rig()
    first = observer.observe(7, closed_frame_id=7)
    calls = list(api.calls)
    duplicate = observer.observe(7, closed_frame_id=7)
    assert duplicate['status'] == 'unproven' and duplicate['errors']
    assert api.calls == calls and observer.receipt(7) == first
    assert len(observer.records) == 2 and observer.metadata()['pacing_disabled'] is False


def test_qt_format_request_cannot_override_actual_wgl_interval():
    observer, state, api, made = rig(0)
    state.current.format_interval = state.scene.format_interval = 1
    zero = observer.observe(7, closed_frame_id=7)
    assert P.validate_receipt(zero, 7, unpaced=True) == 0
    observer, state, api, made = rig(1)
    state.current.format_interval = state.scene.format_interval = 0
    paced = observer.observe(7, closed_frame_id=7)
    assert paced['status'] == 'observed' and P.validate_receipt(paced,7,unpaced=False) == 1
    with pytest.raises(P.PacingUnavailable): P.validate_receipt(paced,7,unpaced=True)
    assert observer.metadata()['pacing_disabled'] is False


_QT_HANDLE_FIELDS = ('qt_current_context','qt_scene_context','qt_current_surface',
    'qt_top_level_surface','qt_current_thread','qt_native_thread','qt_context_thread',
    'qt_surface_thread','qt_thread_id','expected_hwnd')


@pytest.mark.parametrize('field', [*('qt.'+name for name in _QT_HANDLE_FIELDS),
    'native.hglrc','native.hdc','native.window','native.thread_id'])
@pytest.mark.parametrize('malformed', [True,1.0])
def test_after_snapshot_equal_valued_bool_float_cannot_hide_behind_dict_equality(field, malformed):
    record = observed(7)
    # All int-one handles form a consistent synthetic owner. Replacing only an
    # after value with True or1.0 leaves dict equality True, which is precisely
    # why every after scalar must receive its own strict type validation.
    for snapshot in (record['before'],record['after']):
        for name in _QT_HANDLE_FIELDS: snapshot[name]=1
        snapshot['native']=dict(hglrc=1,hdc=1,window=1,thread_id=1)
    assert P.validate_receipt(record,7,unpaced=True)==0
    category,name=field.split('.')
    if category=='qt':record['after'][name]=malformed
    else:record['after']['native'][name]=malformed
    assert record['before']==record['after']
    with pytest.raises(P.PacingUnavailable):P.validate_receipt(record,7,unpaced=True)


@pytest.mark.parametrize('position', [0,1,2])
@pytest.mark.parametrize('defect', ['missing','foreign','stale','paced','adaptive','interval_bool','interval_float','receipt_frame_bool','receipt_frame_float',
    'unowned','changed_dc','missing_hdc','schema_bool','not_presented','not_closed','not_success','frame_bool'])
def test_every_completed_sample_is_independently_validated(position, defect):
    samples = [completed(n) for n in range(3)]
    target = samples[position]
    receipt = target['presentation_pacing']
    if defect == 'missing': target.pop('presentation_pacing')
    elif defect == 'foreign': receipt['frame_id'] = 123
    elif defect == 'stale': target['presentation_pacing'] = observed((position+1)%3)
    elif defect == 'paced': receipt['interval'] = 1
    elif defect == 'adaptive': receipt['interval'] = -1
    elif defect == 'interval_bool': receipt['interval'] = False
    elif defect == 'interval_float': receipt['interval'] = 0.0
    elif defect == 'receipt_frame_bool': receipt['frame_id'] = bool(position)
    elif defect == 'receipt_frame_float': receipt['frame_id'] = float(position)
    elif defect == 'unowned': receipt['owned_after_closed_paint'] = False
    elif defect == 'changed_dc': receipt['after']['native']['hdc'] += 1
    elif defect == 'missing_hdc':
        receipt['before']['native'].pop('hdc');receipt['after']['native'].pop('hdc')
    elif defect == 'schema_bool': receipt['schema'] = True
    elif defect == 'not_presented': target['presented'] = False
    elif defect == 'not_closed': target['scene_and_presentation_syncs_signaled'] = False
    elif defect == 'not_success': target['status'] = 'pending'
    elif defect == 'frame_bool': target['frame_id'] = bool(position)
    with pytest.raises(P.PacingUnavailable): P.validate_completed_samples(samples,range(3),unpaced=True)


@pytest.mark.parametrize('samples,ids', [(None,[]),(True,[]),({},[]),([None],[0]),([False],[0]),([0.0],[0]),
    ([{}],[0]),([completed(0)],[True]),([completed(0)],[0.0])])
def test_completed_collection_rejects_malformed_entries_and_expected_owner_types(samples, ids):
    with pytest.raises(P.PacingUnavailable): P.validate_completed_samples(copy.deepcopy(samples),ids,unpaced=True)


def test_complete_sample_ids_cannot_be_missing_reordered_duplicated_or_empty():
    good = [completed(n) for n in range(3)]
    assert P.validate_completed_samples(good,range(3),unpaced=True) is True
    for samples in (good[:2],list(reversed(good)),[good[0],good[0],good[2]]):
        with pytest.raises(P.PacingUnavailable): P.validate_completed_samples(samples,range(3),unpaced=True)
    # A vacuous list is not evidence for a completed measurement interval.
    with pytest.raises(P.PacingUnavailable): P.validate_completed_samples([],[],unpaced=True)


class CFunctionDouble:
    def __init__(self, result):
        self.result = result
        self.calls = []
        self.argtypes = self.restype = None

    def __call__(self, *args):
        self.calls.append(args)
        return self.result(*args) if callable(self.result) else self.result


def bindings_double(monkeypatch, *, interval=0, arb=b'WGL_EXT_swap_control', ext=None, unavailable=()):
    functions = {name:CFunctionDouble(value) for name,value in {
        'wglGetCurrentContext':101,'wglGetCurrentDC':202,'WindowFromDC':303,'GetCurrentThreadId':404}.items()}
    addresses = {b'wglGetExtensionsStringARB':1001,b'wglGetExtensionsStringEXT':1002,b'wglGetSwapIntervalEXT':1003}
    implementation = {1001:CFunctionDouble(arb),1002:CFunctionDouble(ext),1003:CFunctionDouble(interval)}
    resolve_calls=[];signatures=[];libraries=[]
    def address(name):
        resolve_calls.append(name)
        return None if name in unavailable else addresses[name]
    functions['wglGetProcAddress']=CFunctionDouble(address)
    def dll(name,**kwargs):
        libraries.append((name,kwargs))
        if name=='opengl32.dll':return SimpleNamespace(**{n:f for n,f in functions.items()if n.startswith('wgl')})
        if name=='user32.dll':return SimpleNamespace(WindowFromDC=functions['WindowFromDC'])
        if name=='kernel32.dll':return SimpleNamespace(GetCurrentThreadId=functions['GetCurrentThreadId'])
        raise AssertionError(name)
    def convention(restype,*argtypes):
        def bind_address(value):
            signatures.append((value,restype,argtypes))
            return implementation[value]
        return bind_address
    monkeypatch.setattr(P,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setattr(P.ctypes,'WinDLL',dll)
    monkeypatch.setattr(P.ctypes,'WINFUNCTYPE',convention)
    bindings=P.Win32Bindings()
    return bindings,functions,addresses,implementation,resolve_calls,signatures,libraries


def test_exact_read_only_winapi_and_signed_interval_abi(monkeypatch):
    binding,functions,addresses,implementation,resolved,signatures,libraries=bindings_double(monkeypatch,interval=-1)
    assert libraries==[(n,{'use_last_error':True})for n in('opengl32.dll','user32.dll','kernel32.dll')]
    assert binding.snapshot()==dict(hglrc=101,hdc=202,window=303,thread_id=404)
    assert functions['wglGetCurrentContext'].argtypes==[] and functions['wglGetCurrentContext'].restype is ctypes.c_void_p
    assert functions['wglGetCurrentDC'].argtypes==[] and functions['wglGetCurrentDC'].restype is ctypes.c_void_p
    assert functions['WindowFromDC'].argtypes==[ctypes.c_void_p] and functions['WindowFromDC'].restype is ctypes.c_void_p
    assert functions['GetCurrentThreadId'].argtypes==[] and functions['GetCurrentThreadId'].restype is ctypes.c_uint32
    assert functions['wglGetProcAddress'].argtypes==[ctypes.c_char_p] and functions['wglGetProcAddress'].restype is ctypes.c_void_p
    assert binding.get_interval(202)==(-1,'ARB')
    assert resolved==[b'wglGetExtensionsStringARB',b'wglGetSwapIntervalEXT']
    assert signatures==[(1001,ctypes.c_char_p,(ctypes.c_void_p,)),(1003,ctypes.c_int,())]
    assert implementation[1001].calls==[(202,)] and implementation[1003].calls==[()]
    assert all(b'wglSwapIntervalEXT'!=name for name in resolved), 'Observer must never resolve the setter'


def test_extension_arb_unavailable_uses_explicit_ext_signature(monkeypatch):
    binding,functions,addresses,implementation,resolved,signatures,libraries=bindings_double(monkeypatch,
        ext=b'other WGL_EXT_swap_control tail',unavailable=(b'wglGetExtensionsStringARB',))
    assert binding.get_interval(202)==(0,'EXT')
    assert resolved==[b'wglGetExtensionsStringARB',b'wglGetExtensionsStringEXT',b'wglGetSwapIntervalEXT']
    assert signatures==[(1002,ctypes.c_char_p,()),(1003,ctypes.c_int,())]
    assert implementation[1002].calls==[()]


@pytest.mark.parametrize('extension',[None,b'',b'WGL_EXT_swap_control_tear',b'prefixWGL_EXT_swap_control',
    'WGL_EXT_swap_control',b'OTHER'])
def test_extension_name_must_be_a_complete_actual_byte_token_before_interval_getter(monkeypatch,extension):
    binding,functions,addresses,implementation,resolved,signatures,libraries=bindings_double(monkeypatch,arb=extension)
    with pytest.raises(P.PacingUnavailable):binding.get_interval(202)
    assert b'wglGetSwapIntervalEXT'not in resolved and implementation[1003].calls==[]


@pytest.mark.parametrize('invalid',[None,0,1,2,3,-1,ctypes.c_void_p(-1).value,False,True,1.0,1003.0])
def test_invalid_wgl_function_pointer_sentinels_never_construct_callable(monkeypatch,invalid):
    binding,functions,addresses,implementation,resolved,signatures,libraries=bindings_double(monkeypatch)
    functions['wglGetProcAddress'].result=invalid
    with pytest.raises(P.PacingUnavailable):binding.resolve(b'wglGetSwapIntervalEXT',ctypes.c_int)
    assert signatures==[]


@pytest.mark.parametrize('interval',[True,False,0.0,None])
def test_native_interval_binding_cannot_silently_coerce_noninteger_fakes(monkeypatch,interval):
    binding,*_=bindings_double(monkeypatch,interval=interval)
    with pytest.raises(P.PacingUnavailable):binding.get_interval(202)


class WeakQtWrapperDouble:
    """One Python wrapper for a stable backend object; it owns no child wrapper."""
    def __init__(self,binding,key):
        self.binding,self.key=binding,key

    def isValid(self):
        return True

    def surface(self):
        return self.binding.wrap('top_window')

    def thread(self):
        return self.binding.wrap('gui_thread')

    def winId(self):
        return 303


class WeakQtCacheDouble:
    """Model a binding's weak wrapper cache without changing backend identity."""
    keys=('current_context','scene_context','top_window','gui_thread')

    def __init__(self,outcome='success'):
        import weakref
        self.cache=weakref.WeakValueDictionary()
        self.weakref=weakref.ref
        self.created=[]
        self.generations=dict.fromkeys(self.keys,0)
        self.events=[]
        self.outcome=outcome
        self.api=NativeDouble()
        self.api.snapshot=self.native_snapshot
        self.api.get_interval=self.native_getter
        self.qt_context=SimpleNamespace(currentContext=lambda:self.wrap('current_context'),
            areSharing=lambda a,b:a.binding is self and b.binding is self and
                {a.key,b.key}=={'current_context','scene_context'})
        self.qt_thread=SimpleNamespace(currentThread=lambda:self.wrap('gui_thread'),currentThreadId=lambda:404)
        widget=SimpleNamespace(context=lambda:self.wrap('scene_context'),
            thread=lambda:self.wrap('gui_thread'),windowHandle=lambda:self.wrap('top_window'))
        widget.window=lambda:widget
        self.canvas=SimpleNamespace(native=widget)

    def wrap(self,key):
        wrapper=self.cache.get(key)
        if wrapper is None:
            wrapper=WeakQtWrapperDouble(self,key)
            self.cache[key]=wrapper
            self.created.append((key,self.weakref(wrapper)))
            self.generations[key]+=1
        return wrapper

    def witness(self,phase):
        import gc
        gc.collect()
        self.events.append(dict(phase=phase,
            alive={key:self.cache.get(key)is not None for key in self.keys},
            wrapper_ids={key:id(self.cache[key])if key in self.cache else None for key in self.keys},
            generations=dict(self.generations)))

    def native_snapshot(self):
        self.witness('native_snapshot')
        self.api.calls.append(('snapshot',))
        return dict(self.api.tuple)

    def native_getter(self,hdc):
        self.witness('native_getter')
        self.api.calls.append(('get_interval',hdc))
        if self.outcome=='getter_error':
            raise RuntimeError('synthetic weak-cache getter failure')
        if self.outcome=='native_after_error':
            self.api.tuple['hdc']=0
        return 0,'ARB'

    def observer(self):
        return P.WindowsPresentationPacing(self.canvas,self.qt_context,self.qt_thread,
            native_factory=lambda:self.api,platform='win32')

    def assert_ephemeral_wrappers_released(self):
        import gc
        gc.collect()
        assert not self.cache
        assert all(reference()is None for _,reference in self.created)


@pytest.mark.parametrize('outcome',['success','getter_error','native_after_error'])
def test_weak_cached_qt_wrappers_live_across_getter_and_both_snapshots_then_release(outcome):
    binding=WeakQtCacheDouble(outcome)
    observer=binding.observer()
    record=observer.observe(7,closed_frame_id=7)
    assert [event['phase']for event in binding.events]==['native_snapshot','native_getter','native_snapshot']
    # The old helper drops all wrappers when _qt_snapshot returns. That fails
    # this liveness assertion deterministically, even if the allocator happens
    # to reuse identical Python addresses on the next snapshot.
    assert all(all(event['alive'].values())for event in binding.events), 'Qt wrappers released before the observation completed'
    assert all(event['generations']==dict.fromkeys(binding.keys,1)for event in binding.events)
    assert binding.events[0]['wrapper_ids']==binding.events[1]['wrapper_ids']==binding.events[2]['wrapper_ids']
    assert record['before']['qt_current_context']==record['after']['qt_current_context']
    assert record['before']['qt_current_thread']==record['after']['qt_current_thread']
    if outcome=='success':
        assert record['status']=='observed'and record['errors']==[]
        assert record['before']==record['after']
        assert P.validate_receipt(record,7,unpaced=True)==0
    else:
        assert record['status']=='unproven'and record['errors']
        with pytest.raises(P.PacingUnavailable):P.validate_receipt(record,7,unpaced=True)
        if outcome=='getter_error':
            assert any('synthetic weak-cache getter failure'in error for error in record['errors'])
        else:
            assert record['before']['native']['hdc']==202 and record['after']['native']['hdc']==0
    binding.assert_ephemeral_wrappers_released()


def test_weak_cached_wrappers_do_not_accumulate_across_owned_frames_or_saved_receipts():
    binding=WeakQtCacheDouble()
    observer=binding.observer()
    receipts=[]
    for generation,frame in enumerate((7,8,9),1):
        record=observer.observe(frame,closed_frame_id=frame)
        assert record['status']=='observed'and record['before']==record['after']
        assert P.validate_receipt(record,frame,unpaced=True)==0
        assert binding.generations==dict.fromkeys(binding.keys,generation)
        assert all(all(event['alive'].values())for event in binding.events[-3:])
        receipts.append(record)
        binding.assert_ephemeral_wrappers_released()
    assert len(binding.created)==12
    assert len(observer.records)==len(observer.by_frame)==len(receipts)==3
    assert observer.metadata()['pacing_disabled']is True
    assert all(observer.receipt(frame)==receipt for frame,receipt in zip((7,8,9),receipts))
    binding.assert_ephemeral_wrappers_released()
