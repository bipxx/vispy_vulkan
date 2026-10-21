#include <vulkan/vulkan.h>

#if defined(_WIN32)
#define VISPY_LAYER_EXPORT __declspec(dllexport)
#else
#define VISPY_LAYER_EXPORT __attribute__((visibility("default")))
#endif

// MSVC requires export linkage on the first declaration. The pinned layer
// header declares this function without DLL linkage, so declare it first.
struct VkNegotiateLayerInterface;
extern "C" VISPY_LAYER_EXPORT VkResult VKAPI_CALL vkNegotiateLoaderLayerInterfaceVersion(VkNegotiateLayerInterface*);
#include <vulkan/vk_layer.h>
#include "vk_layer_telemetry.hpp"

#include <algorithm>
#include <atomic>
#include <cstring>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>

extern "C" VISPY_LAYER_EXPORT PFN_vkVoidFunction VKAPI_CALL vispy_GetInstanceProcAddr(VkInstance, const char*);
extern "C" VISPY_LAYER_EXPORT PFN_vkVoidFunction VKAPI_CALL vispy_GetDeviceProcAddr(VkDevice, const char*);

namespace {
struct InstanceDispatch {
    VkInstance instance = VK_NULL_HANDLE;
    PFN_vkGetInstanceProcAddr get_instance = nullptr;
    PFN_GetPhysicalDeviceProcAddr get_physical = nullptr;
    PFN_vkDestroyInstance destroy = nullptr;
    PFN_vkEnumerateDeviceExtensionProperties enumerate_extensions = nullptr;
    PFN_vkGetPhysicalDeviceFeatures2 get_features2 = nullptr;
    PFN_vkGetPhysicalDeviceProperties2 get_properties2 = nullptr;
};
struct DeviceDispatch {
    VkDevice device = VK_NULL_HANDLE;
    PFN_vkGetDeviceProcAddr get_device = nullptr;
    PFN_vkDestroyDevice destroy = nullptr;
    PFN_vkGetDeviceQueue get_queue = nullptr;
    PFN_vkGetDeviceQueue2 get_queue2 = nullptr;
    PFN_vkQueueSubmit submit = nullptr;
    PFN_vkQueueSubmit2 submit2 = nullptr;
    PFN_vkQueueSubmit2KHR submit2_khr = nullptr;
    PFN_vkCreateGraphicsPipelines create_graphics_pipelines = nullptr;
    PFN_vkAllocateMemory allocate_memory = nullptr;
    PFN_vkFreeMemory free_memory = nullptr;
    // A non-dispatchable handle can have the same value on two devices.
    // Ownership is per device; all records and aggregate stats share the mutex.
    std::unordered_map<VkDeviceMemory, VkDeviceSize> memory;
    bool bresenham_lines = false;
    bool last_vertex = false;
};
std::atomic<uint64_t> submits{0};
std::atomic<uint64_t> bresenham_pipelines{0};
std::atomic<uint64_t> bresenham_device_creations{0};
std::atomic<bool> request_bresenham{false};
std::atomic<uint64_t> last_vertex_pipelines{0};
std::atomic<uint64_t> last_vertex_device_creations{0};
std::atomic<bool> request_last_vertex{false};
std::mutex dispatch_mutex;
VulkanMemoryTelemetry memory_stats;
VulkanMemoryWindowState memory_window;
uint64_t memory_operations_inflight = 0;
struct ObserveMemoryWindow {
    ~ObserveMemoryWindow() { memory_window.observe(memory_stats); }
};
std::unordered_map<VkInstance, std::shared_ptr<InstanceDispatch>> instances;
std::unordered_map<void*, std::shared_ptr<InstanceDispatch>> instance_keys;
std::unordered_map<VkDevice, std::shared_ptr<DeviceDispatch>> devices;
std::unordered_map<VkQueue, std::shared_ptr<DeviceDispatch>> queues;

// Physical devices share their loader's instance dispatch key. Device and
// queue records use actual handles, retaining distinct next-layer tables.
template <typename T> void* dispatch_key(T handle) {
    return handle ? *reinterpret_cast<void**>(handle) : nullptr;
}
std::shared_ptr<InstanceDispatch> instance_dispatch(VkInstance instance) {
    std::lock_guard lock(dispatch_mutex);
    auto it = instances.find(instance);
    return it == instances.end() ? nullptr : it->second;
}
std::shared_ptr<InstanceDispatch> physical_dispatch(VkPhysicalDevice physical) {
    std::lock_guard lock(dispatch_mutex);
    auto it = instance_keys.find(dispatch_key(physical));
    return it == instance_keys.end() ? nullptr : it->second;
}
std::shared_ptr<DeviceDispatch> device_dispatch(VkDevice device) {
    std::lock_guard lock(dispatch_mutex);
    auto it = devices.find(device);
    return it == devices.end() ? nullptr : it->second;
}
std::shared_ptr<DeviceDispatch> queue_dispatch(VkQueue queue) {
    std::lock_guard lock(dispatch_mutex);
    auto it = queues.find(queue);
    return it == queues.end() ? nullptr : it->second;
}
template <typename Link, typename Info>
Link* find_link(const Info* info, VkStructureType type) {
    if (!info) return nullptr;
    auto* next = reinterpret_cast<const VkBaseInStructure*>(info->pNext);
    while (next) {
        if (next->sType == type) {
            auto* link = reinterpret_cast<Link*>(const_cast<VkBaseInStructure*>(next));
            if (link->function == VK_LAYER_LINK_INFO) return link;
        }
        next = next->pNext;
    }
    return nullptr;
}
const VkBaseInStructure* find_structure(const void* chain, VkStructureType type) {
    for (auto* next = reinterpret_cast<const VkBaseInStructure*>(chain); next; next = next->pNext)
        if (next->sType == type) return next;
    return nullptr;
}
bool has_extension(uint32_t count, const char* const* names, const char* name) {
    for (uint32_t i = 0; i < count; ++i)
        if (names[i] && std::strcmp(names[i], name) == 0) return true;
    return false;
}
bool query_device_extensions(const InstanceDispatch& parent, VkPhysicalDevice physical,
                             std::vector<VkExtensionProperties>& properties) {
    if (!parent.enumerate_extensions) return false;
    for (unsigned attempt = 0; attempt < 4; ++attempt) {
        uint32_t count = 0;
        if (parent.enumerate_extensions(physical, nullptr, &count, nullptr) != VK_SUCCESS) return false;
        properties.resize(count);
        const auto status = parent.enumerate_extensions(physical, nullptr, &count, properties.data());
        if (status == VK_INCOMPLETE) continue;
        if (status != VK_SUCCESS) return false;
        properties.resize(count);
        return true;
    }
    return false;
}
bool advertised_extension(const std::vector<VkExtensionProperties>& properties, const char* name) {
    for (const auto& property : properties)
        if (std::strcmp(property.extensionName, name) == 0) return true;
    return false;
}
const char* supported_line_extension(const InstanceDispatch& parent, VkPhysicalDevice physical) {
    if (!parent.get_features2) return nullptr;
    std::vector<VkExtensionProperties> properties;
    if (!query_device_extensions(parent, physical, properties)) return nullptr;
    return advertised_extension(properties, VK_KHR_LINE_RASTERIZATION_EXTENSION_NAME) ? VK_KHR_LINE_RASTERIZATION_EXTENSION_NAME :
           advertised_extension(properties, VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME) ? VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME : nullptr;
}
bool supported_last_vertex(const InstanceDispatch& parent, VkPhysicalDevice physical) {
    if (!parent.get_features2 || !parent.get_properties2) return false;
    std::vector<VkExtensionProperties> extensions;
    if (!query_device_extensions(parent, physical, extensions) ||
        !advertised_extension(extensions, VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME)) return false;
    VkPhysicalDeviceProvokingVertexFeaturesEXT supported{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROVOKING_VERTEX_FEATURES_EXT};
    VkPhysicalDeviceFeatures2 features{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2};
    features.pNext = &supported;
    parent.get_features2(physical, &features);
    if (supported.provokingVertexLast != VK_TRUE) return false;
    VkPhysicalDeviceProvokingVertexPropertiesEXT supported_properties{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROVOKING_VERTEX_PROPERTIES_EXT};
    VkPhysicalDeviceProperties2 properties{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};
    properties.pNext = &supported_properties;
    parent.get_properties2(physical, &properties);
    // Explicit/dynamic caller state is preserved. Only per-pipeline support
    // permits mixing those pipelines safely with our opt-in GL default LAST.
    return supported_properties.provokingVertexModePerPipeline == VK_TRUE;
}
VkResult VKAPI_CALL create_instance(const VkInstanceCreateInfo* info, const VkAllocationCallbacks* allocator, VkInstance* output) {
    auto* link = find_link<VkLayerInstanceCreateInfo>(info, VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO);
    if (!link || !link->u.pLayerInfo || !output) return VK_ERROR_INITIALIZATION_FAILED;
    auto next = link->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    auto next_physical = link->u.pLayerInfo->pfnNextGetPhysicalDeviceProcAddr;
    if (!next) return VK_ERROR_INITIALIZATION_FAILED;
    auto create = reinterpret_cast<PFN_vkCreateInstance>(next(VK_NULL_HANDLE, "vkCreateInstance"));
    if (!create) return VK_ERROR_INITIALIZATION_FAILED;
    std::shared_ptr<InstanceDispatch> data;
    try { data = std::make_shared<InstanceDispatch>(); }
    catch (const std::bad_alloc&) { return VK_ERROR_OUT_OF_HOST_MEMORY; }
    link->u.pLayerInfo = link->u.pLayerInfo->pNext;
    VkResult result = create(info, allocator, output);
    if (result != VK_SUCCESS) return result;
    data->instance = *output;
    data->get_instance = next;
    data->get_physical = next_physical;
    data->destroy = reinterpret_cast<PFN_vkDestroyInstance>(next(*output, "vkDestroyInstance"));
    data->enumerate_extensions = reinterpret_cast<PFN_vkEnumerateDeviceExtensionProperties>(next(*output, "vkEnumerateDeviceExtensionProperties"));
    const uint32_t api_version = info->pApplicationInfo && info->pApplicationInfo->apiVersion ?
        info->pApplicationInfo->apiVersion : VK_API_VERSION_1_0;
    if (api_version >= VK_API_VERSION_1_1) {
        data->get_features2 = reinterpret_cast<PFN_vkGetPhysicalDeviceFeatures2>(next(*output, "vkGetPhysicalDeviceFeatures2"));
        data->get_properties2 = reinterpret_cast<PFN_vkGetPhysicalDeviceProperties2>(next(*output, "vkGetPhysicalDeviceProperties2"));
    }
    if (has_extension(info->enabledExtensionCount, info->ppEnabledExtensionNames,
                      VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME)) {
        if (!data->get_features2)
            data->get_features2 = reinterpret_cast<PFN_vkGetPhysicalDeviceFeatures2>(next(*output, "vkGetPhysicalDeviceFeatures2KHR"));
        if (!data->get_properties2)
            data->get_properties2 = reinterpret_cast<PFN_vkGetPhysicalDeviceProperties2>(next(*output, "vkGetPhysicalDeviceProperties2KHR"));
    }
    if (!data->destroy) return VK_ERROR_INITIALIZATION_FAILED;
    try {
        std::lock_guard lock(dispatch_mutex);
        instances[*output] = data;
        instance_keys[dispatch_key(*output)] = data;
    } catch (const std::bad_alloc&) {
        { std::lock_guard lock(dispatch_mutex); instances.erase(*output); instance_keys.erase(dispatch_key(*output)); }
        data->destroy(*output, allocator);
        *output = VK_NULL_HANDLE;
        return VK_ERROR_OUT_OF_HOST_MEMORY;
    }
    return VK_SUCCESS;
}
void VKAPI_CALL destroy_instance(VkInstance instance, const VkAllocationCallbacks* allocator) {
    auto data = instance_dispatch(instance);
    if (!data) return;
    {
        std::lock_guard lock(dispatch_mutex);
        instances.erase(instance);
        instance_keys.erase(dispatch_key(instance));
    }
    data->destroy(instance, allocator);
}
VkResult VKAPI_CALL create_device(VkPhysicalDevice physical, const VkDeviceCreateInfo* info,
                                  const VkAllocationCallbacks* allocator, VkDevice* output) {
    auto parent = physical_dispatch(physical);
    auto* link = find_link<VkLayerDeviceCreateInfo>(info, VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO);
    if (!parent || !link || !link->u.pLayerInfo || !output) return VK_ERROR_INITIALIZATION_FAILED;
    auto next_instance = link->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    auto next_device = link->u.pLayerInfo->pfnNextGetDeviceProcAddr;
    if (!next_instance || !next_device) return VK_ERROR_INITIALIZATION_FAILED;
    auto create = reinterpret_cast<PFN_vkCreateDevice>(next_instance(parent->instance, "vkCreateDevice"));
    if (!create) return VK_ERROR_INITIALIZATION_FAILED;
    std::shared_ptr<DeviceDispatch> data;
    VkDeviceCreateInfo selected = *info;
    VkPhysicalDeviceLineRasterizationFeaturesKHR line_features{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_KHR};
    VkPhysicalDeviceProvokingVertexFeaturesEXT last_features{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROVOKING_VERTEX_FEATURES_EXT};
    std::vector<const char*> extensions;
    try {
        data = std::make_shared<DeviceDispatch>();
        auto append_extension = [&](const char* extension) {
            if (has_extension(selected.enabledExtensionCount, selected.ppEnabledExtensionNames, extension)) return;
            if (extensions.empty()) {
                extensions.reserve(static_cast<size_t>(info->enabledExtensionCount) + 2);
                for (uint32_t i = 0; i < info->enabledExtensionCount; ++i) extensions.push_back(info->ppEnabledExtensionNames[i]);
            }
            extensions.push_back(extension);
            selected.enabledExtensionCount = static_cast<uint32_t>(extensions.size());
            selected.ppEnabledExtensionNames = extensions.data();
        };
        if (request_bresenham.load(std::memory_order_relaxed)) {
            const char* extension = supported_line_extension(*parent, physical);
            if (extension) {
                VkPhysicalDeviceLineRasterizationFeaturesKHR supported{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_KHR};
                VkPhysicalDeviceFeatures2 features{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2};
                features.pNext = &supported;
                parent->get_features2(physical, &features);
                const auto* existing = reinterpret_cast<const VkPhysicalDeviceLineRasterizationFeaturesKHR*>(
                    find_structure(info->pNext, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_KHR));
                const auto* aggregate = reinterpret_cast<const VkPhysicalDeviceVulkan14Features*>(
                    find_structure(info->pNext, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_4_FEATURES));
                // Never mutate caller feature structs or add a duplicate alias
                // alongside a caller-provided promoted aggregate.
                const bool enabled = existing ? existing->bresenhamLines == VK_TRUE :
                                     aggregate ? aggregate->bresenhamLines == VK_TRUE : true;
                if (supported.bresenhamLines == VK_TRUE && enabled) {
                    if (!existing && !aggregate) {
                        line_features.bresenhamLines = VK_TRUE;
                        line_features.pNext = const_cast<void*>(info->pNext);
                        selected.pNext = &line_features;
                    }
                    // Reuse whichever alias the caller already enabled.
                    if (!has_extension(info->enabledExtensionCount, info->ppEnabledExtensionNames,
                                       VK_KHR_LINE_RASTERIZATION_EXTENSION_NAME) &&
                        !has_extension(info->enabledExtensionCount, info->ppEnabledExtensionNames,
                                       VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME)) {
                        append_extension(extension);
                    }
                    data->bresenham_lines = true;
                }
            }
        }
        if (request_last_vertex.load(std::memory_order_relaxed) && supported_last_vertex(*parent, physical)) {
            const auto* existing = reinterpret_cast<const VkPhysicalDeviceProvokingVertexFeaturesEXT*>(
                find_structure(info->pNext, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROVOKING_VERTEX_FEATURES_EXT));
            if (!existing || existing->provokingVertexLast == VK_TRUE) {
                if (!existing) {
                    last_features.provokingVertexLast = VK_TRUE;
                    last_features.pNext = const_cast<void*>(selected.pNext);
                    selected.pNext = &last_features;
                }
                append_extension(VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME);
                data->last_vertex = true;
            }
        }
    }
    catch (const std::bad_alloc&) { return VK_ERROR_OUT_OF_HOST_MEMORY; }
    link->u.pLayerInfo = link->u.pLayerInfo->pNext;
    VkResult result = create(physical, &selected, allocator, output);
    if (result != VK_SUCCESS) return result;
    data->device = *output;
    data->get_device = next_device;
    data->destroy = reinterpret_cast<PFN_vkDestroyDevice>(next_device(*output, "vkDestroyDevice"));
    data->get_queue = reinterpret_cast<PFN_vkGetDeviceQueue>(next_device(*output, "vkGetDeviceQueue"));
    data->get_queue2 = reinterpret_cast<PFN_vkGetDeviceQueue2>(next_device(*output, "vkGetDeviceQueue2"));
    data->submit = reinterpret_cast<PFN_vkQueueSubmit>(next_device(*output, "vkQueueSubmit"));
    data->submit2 = reinterpret_cast<PFN_vkQueueSubmit2>(next_device(*output, "vkQueueSubmit2"));
    data->submit2_khr = reinterpret_cast<PFN_vkQueueSubmit2KHR>(next_device(*output, "vkQueueSubmit2KHR"));
    data->create_graphics_pipelines = reinterpret_cast<PFN_vkCreateGraphicsPipelines>(next_device(*output, "vkCreateGraphicsPipelines"));
    data->allocate_memory = reinterpret_cast<PFN_vkAllocateMemory>(next_device(*output, "vkAllocateMemory"));
    data->free_memory = reinterpret_cast<PFN_vkFreeMemory>(next_device(*output, "vkFreeMemory"));
    if (!data->create_graphics_pipelines) { data->bresenham_lines = false; data->last_vertex = false; }
    if (!data->destroy || !data->get_queue || !data->submit) {
        if (data->destroy) data->destroy(*output, allocator);
        *output = VK_NULL_HANDLE;
        return VK_ERROR_INITIALIZATION_FAILED;
    }
    try {
        std::lock_guard lock(dispatch_mutex);
        devices[*output] = data;
    } catch (const std::bad_alloc&) {
        data->destroy(*output, allocator);
        *output = VK_NULL_HANDLE;
        return VK_ERROR_OUT_OF_HOST_MEMORY;
    }
    if (data->bresenham_lines) bresenham_device_creations.fetch_add(1, std::memory_order_relaxed);
    if (data->last_vertex) last_vertex_device_creations.fetch_add(1, std::memory_order_relaxed);
    return VK_SUCCESS;
}
void VKAPI_CALL destroy_device(VkDevice device, const VkAllocationCallbacks* allocator) {
    auto data = device_dispatch(device);
    if (!data) return;
    {
        std::lock_guard lock(dispatch_mutex);
        devices.erase(device);
        memory_window.invalidate(WindowDeviceRetired);
        for (auto it = queues.begin(); it != queues.end();) {
            if (it->second == data) it = queues.erase(it);
            else ++it;
        }
    }
    data->destroy(device, allocator);
    {
        std::lock_guard lock(dispatch_mutex);
        ObserveMemoryWindow observe;
        // Retire bookkeeping after actual device destruction. These records
        // were never observed freed; do not manufacture vkFreeMemory events.
        for (const auto& entry : data->memory) {
            --memory_stats.live_allocations;
            memory_stats.live_bytes -= entry.second;
            ++memory_stats.retired_allocations;
            memory_stats.retired_bytes += entry.second;
        }
        data->memory.clear();
    }
}
VkResult VKAPI_CALL allocate_memory(VkDevice device, const VkMemoryAllocateInfo* info,
                                   const VkAllocationCallbacks* allocator, VkDeviceMemory* output) {
    auto data = device_dispatch(device);
    if (!data || !data->allocate_memory) return VK_ERROR_DEVICE_LOST;
    {
        std::lock_guard lock(dispatch_mutex);
        ++memory_stats.allocate_calls;
        ++memory_operations_inflight;
        memory_window.observe(memory_stats);
    }
    const VkResult result = data->allocate_memory(device, info, allocator, output);
    std::lock_guard lock(dispatch_mutex);
    --memory_operations_inflight;
    ObserveMemoryWindow observe;
    if (result != VK_SUCCESS) {
        ++memory_stats.allocate_failures;
        if (result == VK_ERROR_DEVICE_LOST) memory_window.invalidate(WindowDeviceLost);
        return result;
    }
    ++memory_stats.allocation_count;
    if (!info || !output || *output == VK_NULL_HANDLE) {
        ++memory_stats.tracking_errors;
        return result;
    }
    memory_stats.allocated_bytes += info->allocationSize;
    try {
        if (!data->memory.emplace(*output, info->allocationSize).second) {
            ++memory_stats.tracking_errors;
            return result;
        }
    } catch (const std::bad_alloc&) {
        // Telemetry must preserve the successful downstream allocation and
        // report incomplete tracking rather than changing its API result.
        ++memory_stats.tracking_errors;
        return result;
    }
    ++memory_stats.live_allocations;
    memory_stats.live_bytes += info->allocationSize;
    memory_stats.peak_live_allocations = std::max(memory_stats.peak_live_allocations, memory_stats.live_allocations);
    memory_stats.peak_live_bytes = std::max(memory_stats.peak_live_bytes, memory_stats.live_bytes);
    return result;
}
void VKAPI_CALL free_memory(VkDevice device, VkDeviceMemory memory, const VkAllocationCallbacks* allocator) {
    auto data = device_dispatch(device);
    if (!data || !data->free_memory) return;
    { std::lock_guard lock(dispatch_mutex); ++memory_operations_inflight; }
    data->free_memory(device, memory, allocator);
    std::lock_guard lock(dispatch_mutex);
    --memory_operations_inflight;
    ObserveMemoryWindow observe;
    ++memory_stats.free_calls;
    if (memory == VK_NULL_HANDLE) {
        ++memory_stats.null_free_calls;
        return;
    }
    auto it = data->memory.find(memory);
    if (it == data->memory.end()) {
        ++memory_stats.unknown_free_calls;
        ++memory_stats.tracking_errors;
        return;
    }
    ++memory_stats.free_count;
    memory_stats.freed_bytes += it->second;
    --memory_stats.live_allocations;
    memory_stats.live_bytes -= it->second;
    data->memory.erase(it);
}
void register_queue(VkQueue queue, const std::shared_ptr<DeviceDispatch>& data) {
    if (queue) { std::lock_guard lock(dispatch_mutex); queues[queue] = data; }
}
void VKAPI_CALL get_device_queue(VkDevice device, uint32_t family, uint32_t index, VkQueue* output) {
    auto data = device_dispatch(device);
    if (!data || !output) return;
    data->get_queue(device, family, index, output);
    register_queue(*output, data);
}
void VKAPI_CALL get_device_queue2(VkDevice device, const VkDeviceQueueInfo2* info, VkQueue* output) {
    auto data = device_dispatch(device);
    if (!data || !data->get_queue2 || !output) return;
    data->get_queue2(device, info, output);
    register_queue(*output, data);
}
VkResult VKAPI_CALL queue_submit(VkQueue queue, uint32_t count, const VkSubmitInfo* info, VkFence fence) {
    auto data = queue_dispatch(queue);
    if (!data || !data->submit) return VK_ERROR_DEVICE_LOST;
    submits.fetch_add(1, std::memory_order_relaxed);
    return data->submit(queue, count, info, fence);
}
VkResult VKAPI_CALL queue_submit2(VkQueue queue, uint32_t count, const VkSubmitInfo2* info, VkFence fence) {
    auto data = queue_dispatch(queue);
    if (!data || !data->submit2) return VK_ERROR_DEVICE_LOST;
    submits.fetch_add(1, std::memory_order_relaxed);
    return data->submit2(queue, count, info, fence);
}
VkResult VKAPI_CALL queue_submit2_khr(VkQueue queue, uint32_t count, const VkSubmitInfo2* info, VkFence fence) {
    auto data = queue_dispatch(queue);
    if (!data || !data->submit2_khr) return VK_ERROR_DEVICE_LOST;
    submits.fetch_add(1, std::memory_order_relaxed);
    return data->submit2_khr(queue, count, info, fence);
}
bool static_basic_line(const VkGraphicsPipelineCreateInfo& info) {
    if (!info.pInputAssemblyState || !info.pRasterizationState) return false;
    if (info.pInputAssemblyState->topology != VK_PRIMITIVE_TOPOLOGY_LINE_LIST &&
        info.pInputAssemblyState->topology != VK_PRIMITIVE_TOPOLOGY_LINE_STRIP) return false;
    if (info.pRasterizationState->lineWidth != 1.0f || info.pRasterizationState->rasterizerDiscardEnable ||
        find_structure(info.pRasterizationState->pNext, VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_LINE_STATE_CREATE_INFO_KHR)) return false;
    if (info.pDynamicState)
        for (uint32_t i = 0; i < info.pDynamicState->dynamicStateCount; ++i) {
            const auto state = info.pDynamicState->pDynamicStates[i];
            // The private opt-in policy is Dawn's fixed1px contract. Pinned
            // Dawn declares LINE_WIDTH dynamic but sets it to1 at every pass
            // (CommandBufferVk.cpp); gloo rejects wider native lines. Preserve
            // dynamic width while selecting the queried rasterization mode.
            if (state == VK_DYNAMIC_STATE_LINE_RASTERIZATION_MODE_EXT || state == VK_DYNAMIC_STATE_LINE_STIPPLE_ENABLE_EXT ||
                state == VK_DYNAMIC_STATE_PRIMITIVE_TOPOLOGY ||
                state == VK_DYNAMIC_STATE_POLYGON_MODE_EXT) return false;
        }
    return true;
}
bool default_provoking_state(const VkGraphicsPipelineCreateInfo& info) {
    if (!info.pRasterizationState || find_structure(info.pRasterizationState->pNext,
            VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_PROVOKING_VERTEX_STATE_CREATE_INFO_EXT)) return false;
    if (info.pDynamicState)
        for (uint32_t i = 0; i < info.pDynamicState->dynamicStateCount; ++i)
            if (info.pDynamicState->pDynamicStates[i] == VK_DYNAMIC_STATE_PROVOKING_VERTEX_MODE_EXT) return false;
    return true;
}
VkResult VKAPI_CALL create_graphics_pipelines(VkDevice device, VkPipelineCache cache, uint32_t count,
    const VkGraphicsPipelineCreateInfo* info, const VkAllocationCallbacks* allocator, VkPipeline* output) {
    auto data = device_dispatch(device);
    if (!data || !data->create_graphics_pipelines) return VK_ERROR_DEVICE_LOST;
    if ((!data->bresenham_lines && !data->last_vertex) || !info || !count)
        return data->create_graphics_pipelines(device, cache, count, info, allocator, output);
    try {
        bool affected = false;
        for (uint32_t i = 0; i < count; ++i)
            affected |= (data->bresenham_lines && static_basic_line(info[i])) ||
                        (data->last_vertex && default_provoking_state(info[i]));
        if (!affected) return data->create_graphics_pipelines(device, cache, count, info, allocator, output);
        // All replacement arrays keep fixed storage until the synchronous
        // downstream creation returns. Unaffected descriptors and caller
        // pNext nodes remain borrowed and unchanged.
        std::vector<VkGraphicsPipelineCreateInfo> selected(info, info + count);
        std::vector<VkPipelineRasterizationStateCreateInfo> rasterization(count);
        std::vector<VkPipelineRasterizationLineStateCreateInfoKHR> lines(count);
        std::vector<VkPipelineRasterizationProvokingVertexStateCreateInfoEXT> last(count);
        for (uint32_t i = 0; i < count; ++i) {
            const bool use_line = data->bresenham_lines && static_basic_line(info[i]);
            const bool use_last = data->last_vertex && default_provoking_state(info[i]);
            if (!use_line && !use_last) continue;
            rasterization[i] = *info[i].pRasterizationState;
            if (use_line) {
                lines[i].sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_LINE_STATE_CREATE_INFO_KHR;
                lines[i].pNext = rasterization[i].pNext;
                lines[i].lineRasterizationMode = VK_LINE_RASTERIZATION_MODE_BRESENHAM_KHR;
                lines[i].stippledLineEnable = VK_FALSE;
                rasterization[i].pNext = &lines[i];
            }
            if (use_last) {
                last[i].sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_PROVOKING_VERTEX_STATE_CREATE_INFO_EXT;
                last[i].pNext = rasterization[i].pNext;
                last[i].provokingVertexMode = VK_PROVOKING_VERTEX_MODE_LAST_VERTEX_EXT;
                rasterization[i].pNext = &last[i];
            }
            selected[i].pRasterizationState = &rasterization[i];
        }
        const auto result = data->create_graphics_pipelines(device, cache, count, selected.data(), allocator, output);
        if (result == VK_SUCCESS && output)
            for (uint32_t i = 0; i < count; ++i)
                if (output[i] != VK_NULL_HANDLE) {
                    if (data->bresenham_lines && static_basic_line(info[i]))
                        bresenham_pipelines.fetch_add(1, std::memory_order_relaxed);
                    if (data->last_vertex && default_provoking_state(info[i]))
                        last_vertex_pipelines.fetch_add(1, std::memory_order_relaxed);
                }
        return result;
    } catch (const std::bad_alloc&) { return VK_ERROR_OUT_OF_HOST_MEMORY; }
}
PFN_vkVoidFunction VKAPI_CALL get_physical_proc(VkInstance instance, const char* name) {
    if (!name) return nullptr;
    auto data = instance_dispatch(instance);
    return data && data->get_physical ? data->get_physical(instance, name) : nullptr;
}
}  // namespace

extern "C" VISPY_LAYER_EXPORT uint64_t vispy_layer_vk_submit_count() {
    return submits.load(std::memory_order_relaxed);
}
extern "C" VISPY_LAYER_EXPORT uint32_t vispy_layer_vk_memory_snapshot(VulkanMemoryTelemetry* output, uint32_t size) {
    if (!output || size != sizeof(VulkanMemoryTelemetry)) return 0;
    std::lock_guard lock(dispatch_mutex);
    *output = memory_stats;
    output->active_devices = devices.size();
    output->tracking_devices = 0;
    for (const auto& entry : devices)
        output->tracking_devices += entry.second->allocate_memory && entry.second->free_memory;
    return 1;
}
extern "C" VISPY_LAYER_EXPORT uint32_t vispy_layer_vk_memory_window_begin(VulkanMemoryWindow* output, uint32_t size) {
    if (!output || size != sizeof(VulkanMemoryWindow)) return 0;
    std::lock_guard lock(dispatch_mutex);
    const bool available = !devices.empty() && std::all_of(devices.begin(), devices.end(),
        [](const auto& entry) { return entry.second->allocate_memory && entry.second->free_memory; });
    *output = memory_window.begin(memory_stats, available, memory_operations_inflight == 0);
    return 1;
}
extern "C" VISPY_LAYER_EXPORT uint32_t vispy_layer_vk_memory_window_end(uint64_t token, VulkanMemoryWindow* output, uint32_t size) {
    if (!output || size != sizeof(VulkanMemoryWindow)) return 0;
    std::lock_guard lock(dispatch_mutex);
    const bool available = !devices.empty() && std::all_of(devices.begin(), devices.end(),
        [](const auto& entry) { return entry.second->allocate_memory && entry.second->free_memory; });
    *output = memory_window.end(token, memory_stats, available, memory_operations_inflight == 0);
    return 1;
}
extern "C" VISPY_LAYER_EXPORT uint64_t vispy_layer_vk_active_instance_count() {
    std::lock_guard lock(dispatch_mutex);
    return instances.size();
}
extern "C" VISPY_LAYER_EXPORT uint64_t vispy_layer_vk_active_device_count() {
    std::lock_guard lock(dispatch_mutex);
    return devices.size();
}
extern "C" VISPY_LAYER_EXPORT void vispy_layer_vk_enable_bresenham(uint32_t enabled) {
    request_bresenham.store(enabled != 0, std::memory_order_relaxed);
}
extern "C" VISPY_LAYER_EXPORT uint64_t vispy_layer_vk_bresenham_device_count() {
    std::lock_guard lock(dispatch_mutex);
    uint64_t count = 0;
    for (const auto& entry : devices) count += entry.second->bresenham_lines;
    return count;
}
extern "C" VISPY_LAYER_EXPORT uint64_t vispy_layer_vk_bresenham_pipeline_count() {
    return bresenham_pipelines.load(std::memory_order_relaxed);
}
extern "C" VISPY_LAYER_EXPORT uint64_t vispy_layer_vk_bresenham_device_creations() {
    return bresenham_device_creations.load(std::memory_order_relaxed);
}
extern "C" VISPY_LAYER_EXPORT void vispy_layer_vk_enable_last_vertex(uint32_t enabled) {
    request_last_vertex.store(enabled != 0, std::memory_order_relaxed);
}
extern "C" VISPY_LAYER_EXPORT uint64_t vispy_layer_vk_last_vertex_device_creations() {
    return last_vertex_device_creations.load(std::memory_order_relaxed);
}
extern "C" VISPY_LAYER_EXPORT uint64_t vispy_layer_vk_last_vertex_pipeline_count() {
    return last_vertex_pipelines.load(std::memory_order_relaxed);
}
extern "C" VISPY_LAYER_EXPORT PFN_vkVoidFunction VKAPI_CALL vispy_GetDeviceProcAddr(VkDevice device, const char* name) {
    if (!name) return nullptr;
    if (std::strcmp(name, "vkGetDeviceProcAddr") == 0) return reinterpret_cast<PFN_vkVoidFunction>(vispy_GetDeviceProcAddr);
    auto data = device_dispatch(device);
    if (!data) return nullptr;
    if (std::strcmp(name, "vkDestroyDevice") == 0) return data->destroy ? reinterpret_cast<PFN_vkVoidFunction>(destroy_device) : nullptr;
    if (std::strcmp(name, "vkGetDeviceQueue") == 0) return data->get_queue ? reinterpret_cast<PFN_vkVoidFunction>(get_device_queue) : nullptr;
    if (std::strcmp(name, "vkGetDeviceQueue2") == 0) return data->get_queue2 ? reinterpret_cast<PFN_vkVoidFunction>(get_device_queue2) : nullptr;
    if (std::strcmp(name, "vkQueueSubmit") == 0) return data->submit ? reinterpret_cast<PFN_vkVoidFunction>(queue_submit) : nullptr;
    if (std::strcmp(name, "vkQueueSubmit2") == 0) return data->submit2 ? reinterpret_cast<PFN_vkVoidFunction>(queue_submit2) : nullptr;
    if (std::strcmp(name, "vkQueueSubmit2KHR") == 0) return data->submit2_khr ? reinterpret_cast<PFN_vkVoidFunction>(queue_submit2_khr) : nullptr;
    if (std::strcmp(name, "vkCreateGraphicsPipelines") == 0) return data->create_graphics_pipelines ? reinterpret_cast<PFN_vkVoidFunction>(create_graphics_pipelines) : nullptr;
    if (std::strcmp(name, "vkAllocateMemory") == 0) return data->allocate_memory ? reinterpret_cast<PFN_vkVoidFunction>(allocate_memory) : nullptr;
    if (std::strcmp(name, "vkFreeMemory") == 0) return data->free_memory ? reinterpret_cast<PFN_vkVoidFunction>(free_memory) : nullptr;
    return data->get_device(device, name);
}
extern "C" VISPY_LAYER_EXPORT PFN_vkVoidFunction VKAPI_CALL vispy_GetInstanceProcAddr(VkInstance instance, const char* name) {
    if (!name) return nullptr;
    if (std::strcmp(name, "vkGetInstanceProcAddr") == 0) return reinterpret_cast<PFN_vkVoidFunction>(vispy_GetInstanceProcAddr);
    if (std::strcmp(name, "vkGetDeviceProcAddr") == 0) return reinterpret_cast<PFN_vkVoidFunction>(vispy_GetDeviceProcAddr);
    if (std::strcmp(name, "vkCreateInstance") == 0) return reinterpret_cast<PFN_vkVoidFunction>(create_instance);
    auto data = instance_dispatch(instance);
    if (!data) return nullptr;
    if (std::strcmp(name, "vkDestroyInstance") == 0) return reinterpret_cast<PFN_vkVoidFunction>(destroy_instance);
    if (std::strcmp(name, "vkCreateDevice") == 0) return reinterpret_cast<PFN_vkVoidFunction>(create_device);
    // GIPA can also return device functions. Preserve interception on that path.
    if (std::strcmp(name, "vkDestroyDevice") == 0) return reinterpret_cast<PFN_vkVoidFunction>(destroy_device);
    if (std::strcmp(name, "vkGetDeviceQueue") == 0) return reinterpret_cast<PFN_vkVoidFunction>(get_device_queue);
    if (std::strcmp(name, "vkGetDeviceQueue2") == 0) return data->get_instance(instance, name) ? reinterpret_cast<PFN_vkVoidFunction>(get_device_queue2) : nullptr;
    if (std::strcmp(name, "vkQueueSubmit") == 0) return reinterpret_cast<PFN_vkVoidFunction>(queue_submit);
    if (std::strcmp(name, "vkQueueSubmit2") == 0) return data->get_instance(instance, name) ? reinterpret_cast<PFN_vkVoidFunction>(queue_submit2) : nullptr;
    if (std::strcmp(name, "vkQueueSubmit2KHR") == 0) return data->get_instance(instance, name) ? reinterpret_cast<PFN_vkVoidFunction>(queue_submit2_khr) : nullptr;
    if (std::strcmp(name, "vkCreateGraphicsPipelines") == 0) return data->get_instance(instance, name) ? reinterpret_cast<PFN_vkVoidFunction>(create_graphics_pipelines) : nullptr;
    if (std::strcmp(name, "vkAllocateMemory") == 0) return data->get_instance(instance, name) ? reinterpret_cast<PFN_vkVoidFunction>(allocate_memory) : nullptr;
    if (std::strcmp(name, "vkFreeMemory") == 0) return data->get_instance(instance, name) ? reinterpret_cast<PFN_vkVoidFunction>(free_memory) : nullptr;
    return data->get_instance(instance, name);
}
extern "C" VISPY_LAYER_EXPORT VkResult VKAPI_CALL vkNegotiateLoaderLayerInterfaceVersion(VkNegotiateLayerInterface* version) {
    if (!version || version->sType != LAYER_NEGOTIATE_INTERFACE_STRUCT || version->loaderLayerInterfaceVersion < 2)
        return VK_ERROR_INITIALIZATION_FAILED;
    version->loaderLayerInterfaceVersion = 2;
    version->pfnGetInstanceProcAddr = vispy_GetInstanceProcAddr;
    version->pfnGetDeviceProcAddr = vispy_GetDeviceProcAddr;
    version->pfnGetPhysicalDeviceProcAddr = get_physical_proc;
    return VK_SUCCESS;
}
