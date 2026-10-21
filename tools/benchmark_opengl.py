"""Opt-in upstream observation. All GL/Qt objects are explicit dependencies.

No provider imports occur here. GL calls remain pass-through; counters describe
observed API attempts and requested payloads/descriptors, never opaque driver
memory. Timestamp objects belong exclusively to the scene context.
"""
from collections import deque
import copy
import ctypes
import operator
import time


def integer(value):
    if isinstance(value, bool):
        raise ValueError('integer API value required')
    return operator.index(value)


def payload_bytes(value):
    if value is None:
        return 0
    size = getattr(value, 'nbytes', None)
    if size is not None:
        return integer(size)
    return memoryview(value).nbytes


class OpenGLAttribution:
    """Observe public VisPy GL adapters and raw PyOpenGL aliases once per call.

    Native Qt/compositor internals are not Python calls and are excluded. A
    nested adapter -> PyOpenGL invocation is counted once in its operation
    category. Exceptions propagate, with elapsed time/failed attempts retained.
    """
    FIELDS = (
        'gl_texture_upload_calls', 'gl_texture_upload_bytes', 'gl_texture_upload_cpu_ns',
        'gl_buffer_upload_calls', 'gl_buffer_upload_bytes', 'gl_buffer_upload_cpu_ns',
        'gl_texture_storage_calls', 'gl_buffer_storage_calls', 'gl_buffer_storage_requested_bytes',
        'gl_shader_compile_calls', 'gl_shader_compile_cpu_ns', 'gl_program_link_calls', 'gl_program_link_cpu_ns',
        'gl_draw_calls', 'gl_clear_calls', 'gl_application_presents', 'gl_unattributed_presents',
        'gl_finish_calls', 'gl_blocking_client_wait_calls', 'gl_zero_timeout_poll_calls',
        'gl_server_wait_calls', 'gl_readback_calls', 'gl_failed_api_calls',
    )
    RESOURCE_NAMES = ('buffer', 'texture', 'framebuffer', 'renderbuffer', 'shader', 'program')

    def __init__(self, owners, *, clock=time.perf_counter_ns, descriptor_limit=65536):
        if type(descriptor_limit) is not int or descriptor_limit < 1:
            raise ValueError('positive descriptor bound required')
        self.clock, self.descriptor_limit = clock, descriptor_limit
        self.totals = dict.fromkeys(self.FIELDS, 0)
        self.live = {name: set() for name in self.RESOURCE_NAMES}
        for name in self.RESOURCE_NAMES:
            for suffix in ('create_calls', 'created_names', 'delete_calls', 'deleted_names', 'live_descriptors', 'peak_live_descriptors'):
                self.totals['gl_'+name+'_'+suffix] = 0
        self.restores, self.depth, self.errors, self.installed = [], {}, [], []
        self.storage_descriptors = deque(maxlen=64)
        self.coverage = []
        try:
            for flavour, owner in owners:
                for name in self._operations():
                    if callable(getattr(owner, name, None)):
                        self._replace(owner, name, flavour)
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _operations():
        return (
            'glBufferData','glBufferSubData', 'glTexImage1D','glTexImage2D','glTexImage3D',
            'glTexSubImage1D','glTexSubImage2D','glTexSubImage3D',
            'glCompileShader','glLinkProgram','glDrawArrays','glDrawElements',
            'glDrawArraysInstanced','glDrawElementsInstanced','glClear','glFinish','glClientWaitSync','glWaitSync','glReadPixels',
            'glCreateBuffer','glCreateTexture','glCreateFramebuffer','glCreateRenderbuffer','glCreateShader','glCreateProgram',
            'glGenBuffers','glGenTextures','glGenFramebuffers','glGenRenderbuffers',
            'glDeleteBuffer','glDeleteTexture','glDeleteFramebuffer','glDeleteRenderbuffer','glDeleteShader','glDeleteProgram',
            'glDeleteBuffers','glDeleteTextures','glDeleteFramebuffers','glDeleteRenderbuffers',
        )

    @staticmethod
    def _category(name):
        for suffix, kind in [('Buffers','buffer'),('Textures','texture'),('Framebuffers','framebuffer'),('Renderbuffers','renderbuffer'),
                             ('Buffer','buffer'),('Texture','texture'),('Framebuffer','framebuffer'),('Renderbuffer','renderbuffer'),
                             ('Shader','shader'),('Program','program')]:
            if name.startswith(('glCreate','glGen','glDelete')) and name.endswith(suffix):
                return ('delete_' if name.startswith('glDelete') else 'create_')+kind
        if name.startswith('glTex'):
            return 'texture_data'
        if name.startswith('glBuffer'):
            return 'buffer_data'
        return name

    @staticmethod
    def _names(value):
        if hasattr(value, 'tolist'):
            value = value.tolist()
        if not isinstance(value, (list, tuple)):
            value = [value]
        return [integer(item) for item in value if integer(item) != 0]

    def _replace(self, owner, name, flavour):
        old = getattr(owner, name)
        namespace = getattr(owner, '__dict__', {})
        own, old_own = name in namespace, namespace.get(name)
        category = self._category(name)
        def observe(*args, **kwargs):
            outer = self.depth.get(category, 0) == 0
            self.depth[category] = self.depth.get(category, 0)+1
            start = self.clock()
            success = False
            returned = None
            try:
                returned = old(*args, **kwargs)
                success = True
                return returned
            finally:
                self.depth[category] -= 1
                if outer:
                    elapsed = max(0, self.clock()-start)
                    if not success:
                        self.totals['gl_failed_api_calls'] += 1
                    try:
                        self._record(name, flavour, args, kwargs, returned, success, elapsed)
                    except Exception as error:
                        # Never replace an original GL exception with bookkeeping.
                        if len(self.errors) < 64:
                            self.errors.append(dict(operation=name,error=str(error)))
        setattr(owner, name, observe)
        self.restores.append((owner,name,own,old_own))
        self.installed.append((owner,name,observe))
        self.coverage.append(flavour+'.'+name)

    def _record(self, name, flavour, args, kwargs, returned, success, elapsed):
        def arg(index, key):
            return args[index] if len(args)>index else kwargs[key]
        if name.startswith('glBuffer'):
            storage = name == 'glBufferData'
            if flavour == 'vispy':
                data = arg(1 if storage else 2, 'data')
                size = integer(data) if storage and isinstance(data, int) else payload_bytes(data)
                payload = not(storage and isinstance(data, int))
            else:
                size = integer(arg(1 if storage else 2, 'size'))
                data = arg(2 if storage else 3, 'data')
                payload = data is not None
            if storage:
                self.totals['gl_buffer_storage_calls'] += 1
                self.totals['gl_buffer_storage_requested_bytes'] += size
            if payload:
                self.totals['gl_buffer_upload_calls'] += 1
                self.totals['gl_buffer_upload_bytes'] += size
                self.totals['gl_buffer_upload_cpu_ns'] += elapsed
        elif name.startswith('glTex'):
            storage = 'SubImage' not in name
            data = kwargs.get('pixels',kwargs.get('data',args[-1] if args else None))
            # VisPy adapters accept a shape tuple for an allocation-only call.
            allocation = data is None or flavour == 'vispy' and isinstance(data,(tuple,list))
            if storage:
                self.totals['gl_texture_storage_calls'] += 1
                dimensions = int(name[len('glTexImage')])
                if flavour == 'vispy':
                    shape = data if allocation else data.shape[:dimensions]
                    shape = [integer(v) for v in shape][::-1]
                    internal = arg(2,'internalformat')
                else:
                    keys = ('width','height','depth')[:dimensions]
                    shape = [integer(arg(3+i,key)) for i,key in enumerate(keys)]
                    internal = arg(2,'internalformat')
                self.storage_descriptors.append(dict(operation=name,dimensions=shape,internal_format=integer(internal),
                    success=success,scope='requested texture storage descriptor; no inferred driver bytes'))
            if not allocation:
                self.totals['gl_texture_upload_calls'] += 1
                self.totals['gl_texture_upload_bytes'] += payload_bytes(data)
                self.totals['gl_texture_upload_cpu_ns'] += elapsed
        elif name == 'glCompileShader':
            self.totals['gl_shader_compile_calls'] += 1
            self.totals['gl_shader_compile_cpu_ns'] += elapsed
        elif name == 'glLinkProgram':
            self.totals['gl_program_link_calls'] += 1
            self.totals['gl_program_link_cpu_ns'] += elapsed
        elif name.startswith('glDraw'):
            self.totals['gl_draw_calls'] += 1
        elif name == 'glClear':
            self.totals['gl_clear_calls'] += 1
        elif name == 'glFinish':
            self.totals['gl_finish_calls'] += 1
        elif name == 'glClientWaitSync':
            timeout = integer(arg(2,'timeout'))
            self.totals['gl_zero_timeout_poll_calls' if timeout == 0 else 'gl_blocking_client_wait_calls'] += 1
        elif name == 'glWaitSync':
            self.totals['gl_server_wait_calls'] += 1
        elif name == 'glReadPixels':
            self.totals['gl_readback_calls'] += 1
        else:
            category = self._category(name)
            action, kind = category.split('_',1)
            self.totals['gl_'+kind+'_'+action+'_calls'] += 1
            if success:
                if action == 'create':
                    names = self._names(returned)
                    self.live[kind].update(names)
                else:
                    value = args[-1] if args else next((kwargs[key] for key in
                        ('textures','buffers','framebuffers','renderbuffers','shader','program','id') if key in kwargs),None)
                    names = self._names(value)
                    self.live[kind].difference_update(names)
                self.totals['gl_'+kind+'_'+('created' if action=='create' else 'deleted')+'_names'] += len(names)
                self.totals['gl_'+kind+'_live_descriptors'] = len(self.live[kind])
                self.totals['gl_'+kind+'_peak_live_descriptors'] = max(self.totals['gl_'+kind+'_peak_live_descriptors'],len(self.live[kind]))
                if sum(map(len,self.live.values())) > self.descriptor_limit:
                    raise RuntimeError('observed live descriptor bound exceeded')

    def snapshot(self):
        changed=[name for owner,name,wrapper in self.installed if getattr(owner,name,None) is not wrapper]
        if changed:
            raise RuntimeError('upstream GL call hooks changed during observation: '+', '.join(changed))
        if self.errors:
            raise RuntimeError('incomplete upstream GL attribution: '+repr(self.errors))
        return dict(self.totals)

    def metadata(self):
        return dict(scope='observed VisPy/PyOpenGL calls only; excludes native Qt/compositor and opaque driver work',
            call_semantics='attempt counts; CPU inclusive wall time includes failures and wrapper overhead; nested adapters counted once',
            allocation_scope='successful observed object-name creation/deletion and requested buffer storage; not physical or opaque driver allocation',
            upload_scope='actual call payload byte extent, not inferred GPU residency, bus transfers or conversion work',
            coverage=list(self.coverage),errors=copy.deepcopy(self.errors),descriptor_limit=self.descriptor_limit,
            recent_texture_storage_descriptors=list(self.storage_descriptors),
            call_hooks_unchanged=all(getattr(owner,name,None) is wrapper for owner,name,wrapper in self.installed),
            gauges=['gl_'+n+'_live_descriptors' for n in self.RESOURCE_NAMES],
            high_water_marks=['gl_'+n+'_peak_live_descriptors' for n in self.RESOURCE_NAMES])

    def close(self):
        for owner,name,own,old in reversed(self.restores):
            if own:setattr(owner,name,old)
            else:delattr(owner,name)
        self.restores.clear()


class OpenGLPaintQueries:
    """Bounded nonblocking timestamp pool in the exact scene context.

    The first real canvas.set_current inside paintGL starts a reserved query;
    returning from the unchanged whole paintGL ends it after the alpha tail.
    Qt compositor/presentation-engine/scanout GPU work is expressly excluded.
    """
    def __init__(self, gl, canvas, current_context, *, capacity=3, result_limit=4096):
        if type(capacity) is not int or not 1<=capacity<=3 or type(result_limit) is not int or result_limit<capacity:
            raise ValueError('bounded timestamp pool required')
        self.gl,self.canvas,self.current_context=gl,canvas,current_context
        self.context=canvas.native.context()
        self.capacity,self.result_limit=capacity,result_limit
        self.pending={};self.results={};self.observed=[];self.free=deque();self.ids=[]
        self.reserved=None;self.paint_depth=0;self.failure=None;self.restores=[];self.on_paint_end=None;self.closed=False
        required=('glGenQueries','glQueryCounter','glGetQueryObjectiv','glGetQueryObjectui64v','glGetQueryiv','glDeleteQueries')
        if not all(callable(getattr(gl,name,None)) for name in required):
            raise RuntimeError('actual upstream timestamp API unavailable')
        if self.current_context()!=self.context:
            raise RuntimeError('timestamp pool requires the actual scene context current')
        self.bits=integer(gl.glGetQueryiv(gl.GL_TIMESTAMP,gl.GL_QUERY_COUNTER_BITS))
        if not 1<=self.bits<=64:
            raise RuntimeError('actual upstream timestamp counter is unsupported')
        try:
            self.ids=[integer(n) for n in gl.glGenQueries(capacity*2)]
            if len(self.ids)!=capacity*2 or len(set(self.ids))!=len(self.ids) or any(n<=0 for n in self.ids):
                raise RuntimeError('invalid generated timestamp query identities')
            self.free.extend(zip(self.ids[::2],self.ids[1::2]))
            old_current=canvas.set_current
            def set_current(*args,**kwargs):
                result=old_current(*args,**kwargs)
                if self.paint_depth and self.reserved is not None:
                    item=self.pending[self.reserved]
                    if not item['begun']:
                        self._same_context()
                        # Retire earlier timestamps in the actual paint's owner
                        # context before this frame's first timestamp command.
                        self.poll()
                        gl.glQueryCounter(item['queries'][0],gl.GL_TIMESTAMP)
                        item['begun']=True
                return result
            self._replace(canvas,'set_current',set_current)
            old_paint=canvas._backend.paintGL
            if getattr(getattr(old_paint,'__func__',old_paint),'__code__',None) is None:
                raise RuntimeError('actual Python Qt paintGL boundary unavailable')
            def paint(*args,**kwargs):
                outer=self.paint_depth==0
                frame=self.reserved if outer else None
                self.paint_depth+=1
                success=False
                try:
                    result=old_paint(*args,**kwargs)
                    success=True
                    return result
                except BaseException as error:
                    self.failure='upstream paint failed: '+repr(error)
                    raise
                finally:
                    self.paint_depth-=1
                    if outer and frame is not None:
                        item=self.pending[frame]
                        if success:
                            try:
                                self._same_context()
                                if not item['begun']:
                                    raise RuntimeError('paint did not make the scene context current')
                                gl.glQueryCounter(item['queries'][1],gl.GL_TIMESTAMP)
                                item['ended']=True
                                if self.on_paint_end is not None:self.on_paint_end(frame)
                            except BaseException as error:
                                self.failure='upstream paint telemetry failed: '+repr(error)
                                raise
                        self.reserved=None
            self._replace(canvas._backend,'paintGL',paint)
        except BaseException:
            self.close()
            raise

    def _replace(self,owner,name,value):
        namespace=getattr(owner,'__dict__',{})
        self.restores.append((owner,name,name in namespace,namespace.get(name)))
        setattr(owner,name,value)

    def _same_context(self):
        if self.current_context()!=self.context:
            raise RuntimeError('timestamp operation has a different or missing scene context')

    def ready(self):
        return not self.closed and self.failure is None and self.reserved is None and bool(self.free)

    def begin(self,frame_id):
        if type(frame_id) is not int or frame_id<0 or frame_id in self.pending or frame_id in self.results:
            raise RuntimeError('duplicate or malformed upstream timestamp frame')
        if not self.ready():
            raise RuntimeError('bounded upstream query pool is busy')
        self.pending[frame_id]=dict(frame_id=frame_id,queries=self.free.popleft(),begun=False,ended=False)
        self.reserved=frame_id

    def poll(self):
        if self.failure:raise RuntimeError(self.failure)
        self._same_context()
        for frame_id,item in list(self.pending.items()):
            if not item['ended']:continue
            pair=item['queries']
            # Never request QUERY_RESULT until BOTH results report available.
            if not all(bool(self.gl.glGetQueryObjectiv(q,self.gl.GL_QUERY_RESULT_AVAILABLE)) for q in pair):continue
            values=[]
            for query in pair:
                # Explicit client output avoids PyOpenGL's implicit NumPy
                # GL_UNSIGNED_INT64 allocation/conversion path.
                output=(ctypes.c_uint64*1)()
                self.gl.glGetQueryObjectui64v(query,self.gl.GL_QUERY_RESULT,output)
                values.append(int(output[0]))
            begin,end=values
            record=dict(frame_id=frame_id,status='success',begin_ns=begin,end_ns=end,elapsed_ns=end-begin,
                scope='upstream_vispy_paint',counter_bits=self.bits,scene_context_identity=id(self.context),
                same_scene_context_verified=True,includes_alpha_tail=True,qt_compositor_included=False,scanout_included=False)
            if begin<0 or end<begin or end>=1<<self.bits:
                record.update(status='invalid_timestamp',error='negative, reversed, wrapped or out-of-range timestamp')
            if len(self.results)>=self.result_limit:
                raise RuntimeError('bounded upstream timestamp result retention exceeded')
            self.results[frame_id]=record;self.observed.append(copy.deepcopy(record))
            del self.pending[frame_id];self.free.append(pair)

    def complete(self,first,count):
        return all(frame in self.results for frame in range(first,first+count))

    def join(self,samples):
        for sample in samples:
            frame_id=sample['frame_id'];record=self.results.get(frame_id)
            if record is None or record['status']!='success':
                raise RuntimeError('missing or invalid upstream GPU paint timestamp for '+str(frame_id))
            sample['opengl_gpu_timing']=copy.deepcopy(record)

    def metadata(self):
        return dict(supported=True,enabled=True,query_capacity=self.capacity*2,max_pending_frames=self.capacity,
            result_limit=self.result_limit,counter_bits=self.bits,
            timestamp_units='nanoseconds; actual implementation precision is not inferred from units or counter width',
            method='GL_TIMESTAMP pair around unchanged real Python paintGL after actual set_current; availability-only polls before 64-bit result reads',
            scope='scene-context whole VisPy paint including alpha-tail clear/flush; excludes Qt compositor, presentation engine and scanout',
            collection='availability-only checks after actual paint set_current before its first timestamp, existing owner-context fence polls, and explicit final drain outside throughput interval',
            query_objects_shared_between_contexts=False,overhead_subtracted=False)

    def close(self):
        self.closed=True
        for owner,name,own,old in reversed(self.restores):
            if own:setattr(owner,name,old)
            else:delattr(owner,name)
        self.restores.clear()
        if self.ids:
            self._same_context()
            self.gl.glDeleteQueries(len(self.ids),self.ids)
            self.ids=[]
