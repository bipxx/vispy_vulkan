"""Read-only Windows presentation-window swap-interval evidence.

No Qt imports or native library calls occur at import/construction. The native
getter is reachable only through an owned, already-current presentation callback.
Format requests are metadata. API interval zero is not scanout/compositor proof.
"""
import copy
import ctypes
import sys


class PacingUnavailable(RuntimeError):
    pass


def require(value,message):
    if not value:raise PacingUnavailable(message)


def exact_handle(value):
    return type(value)is int and value>0


def qt_handle(value):
    require(type(value)is int or (type(value).__module__=='PyQt6.sip'and type(value).__name__=='voidptr'),
            'exact Qt integer/voidptr identifier required')
    result=int(value);require(exact_handle(result),'positive Qt handle required');return result


def qt_format_metadata(canvas,qt_context,qt_surface_format):
    """Separately named requests/format metadata; never platform swap proof."""
    result=dict(format_metadata_scope='Qt requests/formats only; no platform pacing proof',format_metadata_errors=[])
    readers={
        'default_format_swap_interval':lambda:qt_surface_format.defaultFormat().swapInterval(),
        'widget_format_swap_interval':lambda:canvas.native.format().swapInterval(),
        'scene_context_format_swap_interval':lambda:canvas.native.context().format().swapInterval(),
        'top_level_surface_format_swap_interval':lambda:canvas.native.window().windowHandle().format().swapInterval(),
        'current_surface_format_swap_interval':lambda:qt_context.currentContext().surface().format().swapInterval(),
    }
    for name,reader in readers.items():
        result[name]=None
        try:
            value=reader();require(type(value)is int,'format interval is not an integer');result[name]=value
        except Exception as error:result['format_metadata_errors'].append(dict(field=name,error=str(error)))
    return result


def validate_receipt(value,frame_id,*,unpaced):
    """Recheck raw per-frame evidence; never trust a cached producer boolean."""
    require(type(frame_id)is int and frame_id>=0,'exact nonnegative owner frame required')
    require(isinstance(value,dict)and type(value.get('schema'))is int and value['schema']==1 and type(value.get('frame_id'))is int and value['frame_id']==frame_id,
            'pacing receipt frame/schema differs')
    require(value.get('status')=='observed'and value.get('platform')=='win32'and value.get('errors')==[] and
            value.get('owned_after_closed_paint')is True,'owned observed Windows presentation receipt required')
    interval=value.get('interval')
    require(type(interval)is int and (interval==0 if unpaced else interval>=0),'actual interval is missing, paced, adaptive or malformed')
    require(value.get('extension')=='WGL_EXT_swap_control'and value.get('extension_source')in('ARB','EXT')and
            value.get('getter_abi')=='WINFUNCTYPE(c_int,void)','actual extension/getter evidence required')
    before,after=value.get('before'),value.get('after')
    for snapshot in(before,after):
        require(isinstance(snapshot,dict),'both presentation ownership snapshots required')
        for name in('qt_current_context','qt_scene_context','qt_current_surface','qt_top_level_surface','qt_current_thread',
                    'qt_native_thread','qt_context_thread','qt_surface_thread','qt_thread_id','expected_hwnd'):
            require(exact_handle(snapshot.get(name)),'missing or malformed Qt owner: '+name)
        require(snapshot.get('qt_context_valid')is True and snapshot.get('qt_scene_sharing')is True and
                snapshot.get('qt_surface_is_top_level')is True,'current Qt context/surface ownership unproven')
        require(snapshot['qt_current_surface']==snapshot['qt_top_level_surface']and
                snapshot['qt_current_thread']==snapshot['qt_native_thread']==snapshot['qt_context_thread']==snapshot['qt_surface_thread'],
                'Qt thread/surface owner mismatch')
        native=snapshot.get('native')
        require(isinstance(native,dict)and all(exact_handle(native.get(n))for n in('hglrc','hdc','window','thread_id')),
                'missing or malformed native current tuple')
        require(native['window']==snapshot['expected_hwnd']and native['thread_id']==snapshot['qt_thread_id'],
                'native current DC window/thread differs from Qt owner')
    require(before==after,'presentation current ownership changed around getter')
    return interval


def validate_completed_samples(samples,expected_ids,*,unpaced=True):
    expected_ids=list(expected_ids)
    require(bool(expected_ids),'nonempty expected frame evidence required')
    require(all(type(frame)is int and frame>=0 for frame in expected_ids),'expected frame IDs must be exact nonnegative integers')
    require(isinstance(samples,list)and all(isinstance(sample,dict)for sample in samples),'completed samples must be a list of mappings')
    require(isinstance(samples,list)and [s.get('frame_id')for s in samples]==list(expected_ids),'complete ordered actual frame IDs required')
    for sample,frame in zip(samples,expected_ids):
        require(type(sample.get('frame_id'))is int and sample.get('status')=='success'and sample.get('presented')is True and
                sample.get('scene_and_presentation_syncs_signaled')is True,'completed presented two-fence sample required')
        validate_receipt(sample.get('presentation_pacing'),frame,unpaced=unpaced)
    return True


class Win32Bindings:
    """Exact Win32/WGL getter ABI; created inside the callback only."""
    def __init__(self):
        require(sys.platform=='win32','Windows WGL pacing observation unsupported on this platform')
        self.gl=ctypes.WinDLL('opengl32.dll',use_last_error=True)
        self.user=ctypes.WinDLL('user32.dll',use_last_error=True)
        self.kernel=ctypes.WinDLL('kernel32.dll',use_last_error=True)
        for name in('wglGetCurrentContext','wglGetCurrentDC'):
            fn=getattr(self.gl,name);fn.argtypes=[];fn.restype=ctypes.c_void_p
        self.gl.wglGetProcAddress.argtypes=[ctypes.c_char_p];self.gl.wglGetProcAddress.restype=ctypes.c_void_p
        self.user.WindowFromDC.argtypes=[ctypes.c_void_p];self.user.WindowFromDC.restype=ctypes.c_void_p
        self.kernel.GetCurrentThreadId.argtypes=[];self.kernel.GetCurrentThreadId.restype=ctypes.c_uint32

    def snapshot(self):
        rc=self.gl.wglGetCurrentContext();dc=self.gl.wglGetCurrentDC()
        return dict(hglrc=int(rc or 0),hdc=int(dc or 0),window=int(self.user.WindowFromDC(dc)or 0),
                    thread_id=int(self.kernel.GetCurrentThreadId()))

    def resolve(self,name,restype,*args):
        address=self.gl.wglGetProcAddress(name)
        invalid=(None,0,1,2,3,ctypes.c_void_p(-1).value)
        require(type(address)is int and address>0 and address not in invalid,'WGL getter address unavailable: '+name.decode())
        return ctypes.WINFUNCTYPE(restype,*args)(address)

    def get_interval(self,hdc):
        # Resolve under this callback's current tuple. Never cache a function
        # pointer across presentation contexts or pixel formats.
        try:
            extensions=self.resolve(b'wglGetExtensionsStringARB',ctypes.c_char_p,ctypes.c_void_p)(hdc)
            source='ARB'
        except PacingUnavailable:
            extensions=self.resolve(b'wglGetExtensionsStringEXT',ctypes.c_char_p)()
            source='EXT'
        require(type(extensions)is bytes and b'WGL_EXT_swap_control'in extensions.split(),'WGL_EXT_swap_control not exposed by current WGL extension string')
        getter=self.resolve(b'wglGetSwapIntervalEXT',ctypes.c_int)
        interval=getter()
        require(type(interval)is int,'native interval getter must return signed c_int')
        return interval,source


class WindowsPresentationPacing:
    def __init__(self,canvas,qt_context,qt_thread,*,native_factory=Win32Bindings,platform=None):
        self.canvas,self.qt_context,self.qt_thread=canvas,qt_context,qt_thread
        self.native_factory=native_factory;self.platform=sys.platform if platform is None else platform
        self.native=None;self.records=[];self.by_frame={};self._all_zero=True

    def _qt_snapshot(self,value,keepalive):
        current=self.qt_context.currentContext();scene=self.canvas.native.context()
        keepalive.extend((current,scene))
        value.update(qt_current_context=id(current)if current is not None else None,qt_scene_context=id(scene)if scene is not None else None)
        widget=self.canvas.native.window();keepalive.append(widget)
        top=widget.windowHandle();keepalive.append(top)
        value['qt_top_level_surface']=id(top)if top is not None else None
        surface=current.surface()if current is not None else None;thread=self.qt_thread.currentThread()
        keepalive.extend((surface,thread))
        value.update(qt_current_surface=id(surface)if surface is not None else None,qt_current_thread=id(thread)if thread is not None else None)
        native_thread=self.canvas.native.thread();context_thread=current.thread()if current is not None else None
        surface_thread=top.thread()if top is not None else None
        keepalive.extend((native_thread,context_thread,surface_thread))
        value.update(qt_native_thread=id(native_thread)if native_thread is not None else None,
            qt_context_thread=id(context_thread)if context_thread is not None else None,qt_surface_thread=id(surface_thread)if surface_thread is not None else None,
            qt_context_valid=current is not None and current.isValid()is True,
            qt_scene_sharing=current is not None and scene is not None and(current==scene or self.qt_context.areSharing(current,scene)is True),
            qt_surface_is_top_level=top is not None and surface==top)
        value['qt_thread_id']=qt_handle(self.qt_thread.currentThreadId())
        value['expected_hwnd']=qt_handle(top.winId())if top is not None else None

    def _snapshot(self,value,keepalive):
        self._qt_snapshot(value,keepalive)
        require(value['qt_context_valid']and value['qt_scene_sharing']and value['qt_surface_is_top_level']and
            value['qt_current_surface']==value['qt_top_level_surface'],'Qt current context/surface is not the presentation owner')
        require(value['qt_current_thread']==value['qt_native_thread']==value['qt_context_thread']==value['qt_surface_thread'],
                'Qt callback/current context is on a different thread')
        require(exact_handle(value['expected_hwnd'])and exact_handle(value['qt_thread_id']),'Qt HWND/thread identifier invalid')
        if self.native is None:self.native=self.native_factory()
        value['native']=self.native.snapshot()
        require(all(exact_handle(value['native'].get(n))for n in('hglrc','hdc','window','thread_id'))and
            value['native']['window']==value['expected_hwnd']and value['native']['thread_id']==value['qt_thread_id'],
            'native current DC/window/thread is not the Qt presentation owner')

    def observe(self,frame_id,*,closed_frame_id):
        # PyQt's weak wrapper cache can release/recycle Python identities
        # between snapshots. Retain this observation's wrappers through the
        # getter, strict validation and immutable receipt copies only.
        keepalive=[]
        record=dict(schema=1,frame_id=frame_id,status='unproven',platform=self.platform,interval=None,errors=[],
            owned_after_closed_paint=False,extension='WGL_EXT_swap_control',extension_source=None,getter_abi='WINFUNCTYPE(c_int,void)',
            before=None,after=None)
        try:
            try:
                require(type(frame_id)is int and frame_id>=0 and type(closed_frame_id)is int and closed_frame_id==frame_id,
                        'actual closed owning paint token required before any native query')
                require(frame_id not in self.by_frame,'duplicate presentation pacing frame refused')
                record['owned_after_closed_paint']=True
                require(self.platform=='win32','actual-platform pacing observation unsupported')
                record['before']={};self._snapshot(record['before'],keepalive)
                try:
                    interval,source=self.native.get_interval(record['before']['native']['hdc'])
                    require(type(interval)is int,'actual signed interval malformed')
                    record.update(interval=interval,extension_source=source)
                finally:
                    record['after']={};self._snapshot(record['after'],keepalive)
                record['status']='observed'
                validate_receipt(record,frame_id,unpaced=False)
            except Exception as error:
                record['status']='unproven';record['errors'].append(str(error))
            frozen=copy.deepcopy(record);self.records.append(frozen)
            if type(frame_id)is int and frame_id not in self.by_frame:self.by_frame[frame_id]=frozen
            self._all_zero=self._all_zero and frozen['status']=='observed'and type(frozen['interval'])is int and frozen['interval']==0
            return copy.deepcopy(frozen)
        finally:
            keepalive.clear()

    def receipt(self,frame_id):
        return copy.deepcopy(self.by_frame.get(frame_id))

    def metadata(self):
        return dict(pacing_evidence_kind='owned_presentation_window_WGL_getter_only',pacing_disabled=bool(self.records)and self._all_zero,
            observed_presentation_callbacks=len(self.records),platform_pacing_evidence='all_owned_interval_zero'if self.records and self._all_zero else'unproven_or_paced',
            platform=self.platform,scanout_measured=False,compositor_throttling_excluded=False)
