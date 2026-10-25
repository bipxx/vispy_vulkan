"""Check an externally installed Linux wheel with a software Vulkan adapter.

Run with Python -I -B; this is functional smoke coverage, not hardware admission.
"""

import argparse,gc,hashlib,importlib.machinery,json,os,pathlib,sys,traceback,zipfile
def require(condition, message):
    if not condition: raise RuntimeError(message)

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cmake'))
from runtime_package import wheel_package_hashes
sys.path.insert(0,str(ROOT/'tools'))
from mesh_layout_process import process_stamp,native_modules,assert_wheel_module_origins
parser=argparse.ArgumentParser()
for flag in ('wheel','output','tag'):parser.add_argument('--'+flag,required=True)
args=parser.parse_args();output=pathlib.Path(args.output);output.mkdir(exist_ok=False)
result={'status':'FAILED_PRESERVED','pid':os.getpid(),'process_stamp':process_stamp(),'tag':args.tag,
        'python':sys.version,'executable':sys.executable,'cases':[],'release_qualified':False}
native=None;canvas=None;text_canvas=None
try:
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert 'cp'+str(sys.version_info.major)+str(sys.version_info.minor)==args.tag
    import numpy as np
    import vispy
    package=pathlib.Path(vispy.__file__).resolve().parent
    assert package.is_relative_to(pathlib.Path(sys.prefix).resolve()) and not package.is_relative_to(ROOT)
    hashes=wheel_package_hashes(args.wheel)
    for n,h in hashes.items():assert hashlib.sha256((package/pathlib.Path(n).relative_to('vispy')).read_bytes()).hexdigest()==h,n
    from vispy import _dawn as native,app,gloo,scene
    from vispy.visuals.text import _sdf_cpu
    assert any(str(_sdf_cpu.__file__).endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES)
    result.update(package=str(package),installed_members_verified=len(hashes),numpy=np.__version__,device=dict(native.device_info()))
    assert result['device']['backend']=='Vulkan' and result['device']['software']
    result['software_vulkan_only']=True
    canvas=app.Canvas(app='dawn_headless',size=(64,64),show=False,config={'samples':0})
    canvas.set_current();gloo.set_viewport(0,0,64,64);gloo.set_state(blend=False,depth_test=False)
    gloo.clear(color=(17/255,33/255,65/255,1))
    clear=gloo.read_pixels((0,0,64,64),alpha=True)
    assert np.all(clear==np.array([17,33,65,255],np.uint8))
    np.save(output/'clear.npy',clear)
    result['cases'].append({'name':'clear','whole_frame_exact':True})
    result['renderbuffers']=[]
    for format_name, format_value in (('color', 'color'), ('rgba8-enum', 0x8058)):
        color = gloo.RenderBuffer((8, 8), format=format_value)
        fbo = gloo.FrameBuffer(color=color)
        start = dict(native.probe())
        with fbo:
            initial = fbo.read(alpha=True)
            np.save(output / (format_name + '-uninitialized.npy'), initial)
            require(initial.shape == (8, 8, 4) and not np.any(initial),
                    format_name + ': new storage must read as zero')
            gloo.clear(color=(1, 0, 0, 1))
            cleared = fbo.read(alpha=True)
            np.save(output / (format_name + '-cleared.npy'), cleared)
            require(np.all(cleared == [255, 0, 0, 255]),
                    format_name + ': clear did not reach the attachment')
        color.resize((4, 4))
        with fbo:
            resized = fbo.read(alpha=True)
            np.save(output / (format_name + '-resized.npy'), resized)
            require(resized.shape == (4, 4, 4) and not np.any(resized),
                    format_name + ': resized storage must read as zero')
            gloo.clear(color=(0, 0, 1, 1))
            color.resize((6, 6))
            pending_resize = fbo.read(alpha=True)
            np.save(output / (format_name + '-pending-resize.npy'), pending_resize)
            require(pending_resize.shape == (6, 6, 4) and not np.any(pending_resize),
                    format_name + ': queued clear leaked into the replacement allocation')
        end = dict(native.probe())
        result['latest_renderbuffer'] = {
            'format': format_name, 'before': start, 'after': end,
            'texture_uploads': end['texture_uploads'] - start['texture_uploads'],
            'texture_upload_bytes': end['texture_upload_bytes'] - start['texture_upload_bytes'],
        }
        require(end['texture_uploads'] == start['texture_uploads'] and
                end['texture_upload_bytes'] == start['texture_upload_bytes'],
                format_name + ': storage allocation performed a CPU texture upload')
        result['renderbuffers'].append({'format': format_name,
                                        'before': start, 'after': end,
                                        'initial_clear_resize_verified': True})
        fbo.delete()
        color.delete()
    gloo.set_viewport(0,0,64,64)
    program=gloo.Program('attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}',
                         'void main(){gl_FragColor=vec4(1,0.25,0,0.8);}')
    program['position']=np.array([[-.75,0],[.75,0]],np.float32)
    previous=None
    for width in (1.5,2.25):
        gloo.set_state(blend=True,blend_func=('src_alpha','one_minus_src_alpha'),depth_test=False,line_smooth=True,line_width=width)
        gloo.clear(color=(0,0,0,0));program.draw('lines')
        image=gloo.read_pixels((0,0,64,64),alpha=True)
        coverage=np.zeros((64,64),np.float64)
        if width==1.5:
            coverage[31:33,8:56]=.75
        else:
            coverage[31:33,8:56]=1
            coverage[30,8:56]=.125;coverage[33,8:56]=.125
        alpha=.8*coverage
        expected=np.zeros((64,64,4),np.uint8)
        expected[:,:,0]=np.rint(255*alpha).astype(np.uint8)
        expected[:,:,1]=np.rint(63.75*alpha).astype(np.uint8)
        expected[:,:,3]=np.rint(255*alpha*alpha).astype(np.uint8)
        np.save(output/('smooth-'+str(width)+'-actual.npy'),image)
        np.save(output/('smooth-'+str(width)+'-expected.npy'),expected)
        delta=int(np.abs(image.astype(np.int16)-expected.astype(np.int16)).max())
        result['latest_line_measurement']={'width':width,'max_rgba_error':delta,'unique_actual_rgba':np.unique(image.reshape(-1,4),axis=0).tolist()}
        assert delta<=1
        probe=dict(native.probe())
        if previous is not None:
            assert probe['render_pipeline_creations']==previous['render_pipeline_creations']
            assert probe['line_consumer_misses']==previous['line_consumer_misses']
        previous=probe
        np.save(output/('smooth-'+str(width)+'.npy'),image)
        result['cases'].append({'name':'smooth-'+str(width),'max_rgba_error':delta,'pipeline_reused':width==2.25})
    program.delete();canvas.close();canvas=None
    text_canvas=scene.SceneCanvas(app='dawn_headless',size=(128,64),show=False,bgcolor='black',config={'samples':0})
    scene.visuals.Text('Ag15',pos=(64,32),font_size=18,color='white',method='cpu',parent=text_canvas.scene)
    text=text_canvas.render(alpha=True)
    assert text.shape==(64,128,4) and np.count_nonzero(text[:,:,:3])>100
    np.save(output/'text.npy',text)
    text_canvas.close();text_canvas=None
    result['cases'].append({'name':'compiled-sdf-text','nonzero_rgb_components':int(np.count_nonzero(text[:,:,:3]))})
    from compatibility_render_smoke import compatibility_render_checks
    result['compatibility'] = compatibility_render_checks(
        app, gloo, scene, np, native, ROOT, output/'instanced-images')
    records=native_modules([ROOT,ROOT.parent/'vispy_vulkan-publication'])
    assert_wheel_module_origins(records,package,hashes,[native.__file__,_sdf_cpu.__file__,package/'VkLayer_vispy_submit.so'])
    result['native_modules']=records;result['native_origins_verified']=True
    result['status']='PASS_INSTALLED_LINUX_SOFTWARE_RENDERBUFFER_CLEAR_SMOOTH_TEXT'
except BaseException:
    result['error']=traceback.format_exc()
finally:
    try:
        if canvas is not None:canvas.close()
        if text_canvas is not None:text_canvas.close()
        if native is not None:
            gc.collect();native.process_events();native.shutdown()
            result['after_shutdown']=dict(native.probe())
            fields=('pending_tickets','queued_frames','live_buffer_bytes','live_cpu_buffer_bytes','live_texture_bytes',
                    'canvas_texture_bytes','transient_buffer_bytes','line_resource_pool_busy_slots','line_resource_pool_bytes')
            assert all(result['after_shutdown'][key]==0 for key in fields)
            result['zero_live_gauges_verified']=list(fields)
    except BaseException:
        result['status']='FAILED_CLEANUP_PRESERVED';result['cleanup_error']=traceback.format_exc()
    (output/'result1.json').write_text(json.dumps(result,indent=2))
print(args.tag,result['status'],flush=True)
if result['status']!='PASS_INSTALLED_LINUX_SOFTWARE_RENDERBUFFER_CLEAR_SMOOTH_TEXT':sys.exit(1)
