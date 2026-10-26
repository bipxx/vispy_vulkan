#include "native_surface.hpp"

#if defined(__APPLE__)
#if !__has_feature(objc_arc)
#error "surface_metal.mm requires Objective-C++ ARC for weak borrowed NSView lifetime"
#endif
#import <Cocoa/Cocoa.h>
#import <QuartzCore/CAMetalLayer.h>
#import <QuartzCore/CATransaction.h>

#include <limits>

// Carry the original Qt attachment through successive VisPy layers. Retiring
// an older owner cannot restore its layer over a newer attachment.
@interface VispySurfaceMetalLayer : CAMetalLayer
@property(nonatomic, strong) CALayer* originalLayer;
@property(nonatomic) BOOL originalWantsLayer;
@end
@implementation VispySurfaceMetalLayer
@end

namespace vispy::platform {
namespace {
void require_main_thread(const char* operation) {
    if (![NSThread isMainThread])
        throw std::runtime_error(std::string(operation) + ": Cocoa surface requires the main GUI thread");
}
void detach_layer(NSView* view, VispySurfaceMetalLayer* layer) {
    if (view && view.layer == layer) {
        view.layer = layer.originalLayer;
        view.wantsLayer = layer.originalWantsLayer;
    }
}
class MetalSurfaceOwner final : public NativeSurfaceOwner {
  public:
    explicit MetalSurfaceOwner(const NativeSurfaceDescriptor& descriptor) : NativeSurfaceOwner(descriptor) {
        require_main_thread("Metal surface attach");
        if (descriptor.kind != NativeSurfaceKind::Metal || !descriptor.window ||
            descriptor.window > std::numeric_limits<uintptr_t>::max())
            throw std::runtime_error("Metal surface: expected a nonzero borrowed NSView descriptor");
        NSView* view = (__bridge NSView*)reinterpret_cast<void*>(static_cast<uintptr_t>(descriptor.window));
        if (![view isKindOfClass:[NSView class]]) throw std::runtime_error("Metal surface: native object is not an NSView");
        view_ = view;
        layer_ = [VispySurfaceMetalLayer layer];
        if ([view.layer isKindOfClass:[VispySurfaceMetalLayer class]]) {
            VispySurfaceMetalLayer* old = (VispySurfaceMetalLayer*)view.layer;
            layer_.originalLayer = old.originalLayer;
            layer_.originalWantsLayer = old.originalWantsLayer;
        } else {
            layer_.originalLayer = view.layer;
            layer_.originalWantsLayer = view.wantsLayer;
        }
        layer_.opaque = NO;
        layer_.frame = view.bounds;
        view.wantsLayer = YES;
        view.layer = layer_;
    }
    ~MetalSurfaceOwner() override {
        __weak NSView* view = view_;
        VispySurfaceMetalLayer* layer = layer_;
        if ([NSThread isMainThread]) {
            detach_layer(view, layer);
        } else {
            // Capture the layer strongly and the widget weakly; async cleanup
            // remains safe even if its submitted work outlives the widget.
            dispatch_async(dispatch_get_main_queue(), ^{ detach_layer(view, layer); });
        }
    }
    wgpu::Surface create_surface(const wgpu::Instance& instance) override {
        check_thread("Metal CreateSurface");
        require_main_thread("Metal CreateSurface");
        if (!view_) throw std::runtime_error("Metal CreateSurface: borrowed NSView has been destroyed");
        if (!instance) throw std::runtime_error("Metal CreateSurface: Dawn instance is null");
        wgpu::SurfaceSourceMetalLayer source;
        source.layer = (__bridge void*)layer_;
        wgpu::SurfaceDescriptor descriptor;
        descriptor.nextInChain = &source;
        auto surface = instance.CreateSurface(&descriptor);
        if (!surface) throw std::runtime_error("Metal CreateSurface: Dawn returned a null surface");
        return surface;
    }
    bool is_alive() const override {
        check_thread("Metal surface liveness");
        require_main_thread("Metal surface liveness");
        NSView* view = view_;
        return view != nil && view.layer == layer_;
    }
    void update(int width, int height, double scale) override {
        check_thread("Metal surface update");
        require_main_thread("Metal surface update");
        check_size(width, height, scale);
        NSView* view = view_;
        if (!view) throw std::runtime_error("Metal surface update: borrowed NSView has been destroyed");
        if (view.layer != layer_) throw std::runtime_error("Metal surface update: layer attachment has been replaced");
        [CATransaction begin];
        [CATransaction setDisableActions:YES];
        layer_.frame = view.bounds;
        layer_.contentsScale = scale;
        layer_.drawableSize = CGSizeMake(width, height);
        [CATransaction commit];
    }
    void detach() override {
        check_thread("Metal surface detach");
        require_main_thread("Metal surface detach");
        detach_layer(view_, layer_);
    }

  private:
    __weak NSView* view_ = nil;
    VispySurfaceMetalLayer* layer_ = nil;
};
}  // namespace
std::shared_ptr<NativeSurfaceOwner> make_native_surface_owner(const NativeSurfaceDescriptor& descriptor) {
    return std::make_shared<MetalSurfaceOwner>(descriptor);
}
}  // namespace vispy::platform
#endif
