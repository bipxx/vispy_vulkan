#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>
#include "../../cpp/platform/vk_layer_telemetry.hpp"

#include <atomic>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <string>
#include <vector>

extern "C" PFN_vkVoidFunction VKAPI_CALL vispy_GetInstanceProcAddr(VkInstance, const char*);
extern "C" PFN_vkVoidFunction VKAPI_CALL vispy_GetDeviceProcAddr(VkDevice, const char*);
extern "C" uint64_t vispy_layer_vk_submit_count();
extern "C" uint64_t vispy_layer_vk_active_instance_count();
extern "C" uint64_t vispy_layer_vk_active_device_count();
extern "C" void vispy_layer_vk_enable_bresenham(uint32_t);
extern "C" uint64_t vispy_layer_vk_bresenham_device_count();
extern "C" uint64_t vispy_layer_vk_bresenham_pipeline_count();
extern "C" uint64_t vispy_layer_vk_bresenham_device_creations();
extern "C" void vispy_layer_vk_enable_last_vertex(uint32_t);
extern "C" uint64_t vispy_layer_vk_last_vertex_device_creations();
extern "C" uint64_t vispy_layer_vk_last_vertex_pipeline_count();
extern "C" uint32_t vispy_layer_vk_memory_snapshot(VulkanMemoryTelemetry*, uint32_t);
extern "C" uint32_t vispy_layer_vk_memory_window_begin(VulkanMemoryWindow*, uint32_t);
extern "C" uint32_t vispy_layer_vk_memory_window_end(uint64_t, VulkanMemoryWindow*, uint32_t);

namespace {
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
struct Handle { void* dispatch; int id; };
int keys[3]{};
Handle instance_handles[] = {{&keys[0], 0}, {&keys[1], 1}};
Handle physical_handles[] = {{&keys[0], 0}, {&keys[1], 1}};
// Shared fake device/queue keys deliberately cannot identify the correct
// downstream table; the layer must retain actual device/queue ownership.
Handle device_handles[] = {{&keys[2], 0}, {&keys[2], 1}};
Handle queue_handles[] = {{&keys[2], 0}, {&keys[2], 1}};
std::atomic<int> native_calls[2]{}, destroyed_devices[2]{}, destroyed_instances[2]{};
std::atomic<uint64_t> memory_calls[2]{}, memory_frees[2]{};
std::atomic<uintptr_t> memory_handle[2]{1000, 1000};
std::atomic<VkResult> memory_result[2]{VK_SUCCESS, VK_SUCCESS};
bool memory_dispatch_available[2]{true, true};
const VkMemoryAllocateInfo* expected_memory_info = nullptr;
const VkAllocationCallbacks* expected_memory_allocator = nullptr;
bool check_memory_forwarding = false;
struct LineMock {
    std::vector<std::string> supported_extensions;
    bool supported = true;
    bool enumeration_failure = false;
    bool device_failure = false;
    unsigned incomplete = 0;
    unsigned queries = 0;
    std::vector<std::string> enabled_extensions;
    bool enabled = false;
    const void* next_after_line = nullptr;
    unsigned feature_structs = 0;
    bool last_supported = true;
    bool per_pipeline = true;
    bool features2_available = true;
    bool properties2_available = true;
    bool graphics_available = true;
    bool write_last_features = true;
    bool write_last_properties = true;
    unsigned last_queries = 0;
    unsigned properties_queries = 0;
    bool last_enabled = false;
    unsigned last_feature_structs = 0;
    const void* next_after_last = nullptr;
    std::vector<VkStructureType> feature_chain;
};
LineMock line_mock[2];
const VkBaseInStructure* find_structure(const void* chain, VkStructureType type) {
    for (auto* next = reinterpret_cast<const VkBaseInStructure*>(chain); next; next = next->pNext)
        if (next->sType == type) return next;
    return nullptr;
}
VkResult VKAPI_CALL enumerate_extensions(VkPhysicalDevice physical, const char*, uint32_t* count, VkExtensionProperties* output) {
    auto& mock = line_mock[reinterpret_cast<Handle*>(physical)->id];
    if (mock.enumeration_failure) return VK_ERROR_INITIALIZATION_FAILED;
    if (!output) { *count = static_cast<uint32_t>(mock.supported_extensions.size()); return VK_SUCCESS; }
    const uint32_t capacity = *count;
    *count = static_cast<uint32_t>(mock.supported_extensions.size());
    for (uint32_t i = 0; i < capacity && i < *count; ++i) {
        output[i] = {};
        std::strncpy(output[i].extensionName, mock.supported_extensions[i].c_str(), VK_MAX_EXTENSION_NAME_SIZE - 1);
    }
    if (mock.incomplete) { --mock.incomplete; return VK_INCOMPLETE; }
    return capacity < *count ? VK_INCOMPLETE : VK_SUCCESS;
}
void VKAPI_CALL features2(VkPhysicalDevice physical, VkPhysicalDeviceFeatures2* output) {
    auto& mock = line_mock[reinterpret_cast<Handle*>(physical)->id];
    auto* lines = const_cast<VkPhysicalDeviceLineRasterizationFeaturesKHR*>(reinterpret_cast<const VkPhysicalDeviceLineRasterizationFeaturesKHR*>(
        find_structure(output->pNext, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_KHR)));
    auto* last = const_cast<VkPhysicalDeviceProvokingVertexFeaturesEXT*>(reinterpret_cast<const VkPhysicalDeviceProvokingVertexFeaturesEXT*>(
        find_structure(output->pNext, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROVOKING_VERTEX_FEATURES_EXT)));
    require(lines || last, "query contains an independently requested compatibility feature");
    if (lines) { ++mock.queries; lines->bresenhamLines = mock.supported ? VK_TRUE : VK_FALSE; }
    if (last) {
        ++mock.last_queries;
        if (mock.write_last_features) last->provokingVertexLast = mock.last_supported ? VK_TRUE : VK_FALSE;
    }
}
void VKAPI_CALL properties2(VkPhysicalDevice physical, VkPhysicalDeviceProperties2* output) {
    auto& mock = line_mock[reinterpret_cast<Handle*>(physical)->id];
    ++mock.properties_queries;
    auto* last = const_cast<VkPhysicalDeviceProvokingVertexPropertiesEXT*>(reinterpret_cast<const VkPhysicalDeviceProvokingVertexPropertiesEXT*>(
        find_structure(output->pNext, VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROVOKING_VERTEX_PROPERTIES_EXT)));
    require(last != nullptr, "properties query requests per-pipeline provoking support");
    if (mock.write_last_properties) last->provokingVertexModePerPipeline = mock.per_pipeline ? VK_TRUE : VK_FALSE;
}
void VKAPI_CALL instance_destroy(VkInstance instance, const VkAllocationCallbacks*) { ++destroyed_instances[reinterpret_cast<Handle*>(instance)->id]; }
void VKAPI_CALL device_destroy(VkDevice device, const VkAllocationCallbacks*) { ++destroyed_devices[reinterpret_cast<Handle*>(device)->id]; }
VkResult VKAPI_CALL instance_create0(const VkInstanceCreateInfo*, const VkAllocationCallbacks*, VkInstance* output) { *output = reinterpret_cast<VkInstance>(&instance_handles[0]); return VK_SUCCESS; }
VkResult VKAPI_CALL instance_create1(const VkInstanceCreateInfo*, const VkAllocationCallbacks*, VkInstance* output) { *output = reinterpret_cast<VkInstance>(&instance_handles[1]); return VK_SUCCESS; }
VkResult VKAPI_CALL device_create(VkPhysicalDevice physical, const VkDeviceCreateInfo* info, const VkAllocationCallbacks*, VkDevice* output) {
    const int id = reinterpret_cast<Handle*>(physical)->id;
    auto& mock = line_mock[id];
    mock.enabled_extensions.clear();
    for (uint32_t i = 0; i < info->enabledExtensionCount; ++i) mock.enabled_extensions.emplace_back(info->ppEnabledExtensionNames[i]);
    mock.enabled = false; mock.feature_structs = 0; mock.next_after_line = nullptr;
    mock.last_enabled = false; mock.last_feature_structs = 0; mock.next_after_last = nullptr; mock.feature_chain.clear();
    for (auto* next = reinterpret_cast<const VkBaseInStructure*>(info->pNext); next; next = next->pNext) {
        mock.feature_chain.push_back(next->sType);
        if (next->sType == VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_KHR) {
            auto* line = reinterpret_cast<const VkPhysicalDeviceLineRasterizationFeaturesKHR*>(next);
            ++mock.feature_structs;
            mock.enabled = line->bresenhamLines == VK_TRUE;
            mock.next_after_line = line->pNext;
        }
        if (next->sType == VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROVOKING_VERTEX_FEATURES_EXT) {
            auto* last = reinterpret_cast<const VkPhysicalDeviceProvokingVertexFeaturesEXT*>(next);
            ++mock.last_feature_structs;
            mock.last_enabled = last->provokingVertexLast == VK_TRUE;
            mock.next_after_last = last->pNext;
        }
    }
    if (mock.device_failure) { *output = VK_NULL_HANDLE; return VK_ERROR_FEATURE_NOT_PRESENT; }
    *output = reinterpret_cast<VkDevice>(&device_handles[id]); return VK_SUCCESS;
}
VkResult graphics_result = VK_SUCCESS;
const VkGraphicsPipelineCreateInfo* expected_graphics = nullptr;
bool graphics_unchanged = false;
std::vector<bool> selected_lines;
std::vector<const void*> selected_line_tail;
std::vector<const VkPipelineRasterizationStateCreateInfo*> selected_raster;
std::vector<bool> selected_last;
std::vector<const void*> selected_last_tail;
std::vector<unsigned> provoking_nodes;
std::vector<bool> last_precedes_line;
VkResult VKAPI_CALL graphics_create(VkDevice, VkPipelineCache, uint32_t count,
    const VkGraphicsPipelineCreateInfo* info, const VkAllocationCallbacks*, VkPipeline* output) {
    graphics_unchanged = info == expected_graphics;
    selected_lines.clear(); selected_line_tail.clear(); selected_raster.clear();
    selected_last.clear(); selected_last_tail.clear(); provoking_nodes.clear(); last_precedes_line.clear();
    for (uint32_t i = 0; i < count; ++i) {
        const auto* chain = info[i].pRasterizationState ? info[i].pRasterizationState->pNext : nullptr;
        const auto* line = reinterpret_cast<const VkPipelineRasterizationLineStateCreateInfoKHR*>(
            find_structure(chain, VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_LINE_STATE_CREATE_INFO_KHR));
        const auto* last = reinterpret_cast<const VkPipelineRasterizationProvokingVertexStateCreateInfoEXT*>(
            find_structure(chain, VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_PROVOKING_VERTEX_STATE_CREATE_INFO_EXT));
        selected_last.push_back(last && last->provokingVertexMode == VK_PROVOKING_VERTEX_MODE_LAST_VERTEX_EXT);
        selected_last_tail.push_back(last ? last->pNext : nullptr);
        last_precedes_line.push_back(last && line && last->pNext == line);
        unsigned last_nodes = 0;
        for (auto* next = reinterpret_cast<const VkBaseInStructure*>(chain); next; next = next->pNext)
            last_nodes += next->sType == VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_PROVOKING_VERTEX_STATE_CREATE_INFO_EXT;
        provoking_nodes.push_back(last_nodes);
        selected_lines.push_back(line && line->lineRasterizationMode == VK_LINE_RASTERIZATION_MODE_BRESENHAM_KHR);
        selected_line_tail.push_back(line ? line->pNext : nullptr);
        selected_raster.push_back(info[i].pRasterizationState);
        if (output) output[i] = graphics_result == VK_SUCCESS ? reinterpret_cast<VkPipeline>(static_cast<uintptr_t>(100 + i)) : VK_NULL_HANDLE;
    }
    return graphics_result;
}
void VKAPI_CALL get_queue(VkDevice device, uint32_t, uint32_t, VkQueue* output) { *output = reinterpret_cast<VkQueue>(&queue_handles[reinterpret_cast<Handle*>(device)->id]); }
void VKAPI_CALL get_queue2(VkDevice device, const VkDeviceQueueInfo2*, VkQueue* output) { get_queue(device, 0, 0, output); }
VkResult VKAPI_CALL submit0(VkQueue, uint32_t, const VkSubmitInfo*, VkFence) { ++native_calls[0]; return VK_SUCCESS; }
VkResult VKAPI_CALL submit1(VkQueue, uint32_t, const VkSubmitInfo*, VkFence) { ++native_calls[1]; return VK_ERROR_DEVICE_LOST; }
VkResult VKAPI_CALL submit2_0(VkQueue, uint32_t, const VkSubmitInfo2*, VkFence) { ++native_calls[0]; return VK_SUCCESS; }
VkResult VKAPI_CALL submit2_1(VkQueue, uint32_t, const VkSubmitInfo2*, VkFence) { ++native_calls[1]; return VK_SUCCESS; }
VkResult VKAPI_CALL memory_allocate(VkDevice device, const VkMemoryAllocateInfo* info,
                                   const VkAllocationCallbacks* allocator, VkDeviceMemory* output) {
    const int id = reinterpret_cast<Handle*>(device)->id;
    ++memory_calls[id];
    if (check_memory_forwarding)
        require(info == expected_memory_info && allocator == expected_memory_allocator,
                "memory descriptor and allocation callbacks forwarded unchanged");
    const auto result = memory_result[id].load();
    // A driver may leave the output untouched on failure. Never treat it as
    // a newly successful allocation or remove an existing record with that id.
    if (result == VK_SUCCESS)
        *output = reinterpret_cast<VkDeviceMemory>(memory_handle[id].fetch_add(1));
    return result;
}
void VKAPI_CALL memory_free(VkDevice device, VkDeviceMemory, const VkAllocationCallbacks* allocator) {
    ++memory_frees[reinterpret_cast<Handle*>(device)->id];
    if (check_memory_forwarding)
        require(allocator == expected_memory_allocator, "free allocation callbacks forwarded unchanged");
}
PFN_vkVoidFunction VKAPI_CALL device_proc0(VkDevice, const char* name) {
    if (!std::strcmp(name, "vkDestroyDevice")) return reinterpret_cast<PFN_vkVoidFunction>(device_destroy);
    if (!std::strcmp(name, "vkGetDeviceQueue")) return reinterpret_cast<PFN_vkVoidFunction>(get_queue);
    if (!std::strcmp(name, "vkGetDeviceQueue2")) return reinterpret_cast<PFN_vkVoidFunction>(get_queue2);
    if (!std::strcmp(name, "vkQueueSubmit")) return reinterpret_cast<PFN_vkVoidFunction>(submit0);
    if (!std::strcmp(name, "vkQueueSubmit2KHR")) return reinterpret_cast<PFN_vkVoidFunction>(submit2_0);
    if (!std::strcmp(name, "device_special")) return reinterpret_cast<PFN_vkVoidFunction>(submit0);
    if (!std::strcmp(name, "vkCreateGraphicsPipelines")) return line_mock[0].graphics_available ? reinterpret_cast<PFN_vkVoidFunction>(graphics_create) : nullptr;
    if (!std::strcmp(name, "vkAllocateMemory")) return memory_dispatch_available[0] ? reinterpret_cast<PFN_vkVoidFunction>(memory_allocate) : nullptr;
    if (!std::strcmp(name, "vkFreeMemory")) return memory_dispatch_available[0] ? reinterpret_cast<PFN_vkVoidFunction>(memory_free) : nullptr;
    return nullptr;
}
PFN_vkVoidFunction VKAPI_CALL device_proc1(VkDevice device, const char* name) {
    if (!std::strcmp(name, "vkAllocateMemory")) return memory_dispatch_available[1] ? reinterpret_cast<PFN_vkVoidFunction>(memory_allocate) : nullptr;
    if (!std::strcmp(name, "vkFreeMemory")) return memory_dispatch_available[1] ? reinterpret_cast<PFN_vkVoidFunction>(memory_free) : nullptr;
    if (!std::strcmp(name, "vkCreateGraphicsPipelines")) return line_mock[1].graphics_available ? reinterpret_cast<PFN_vkVoidFunction>(graphics_create) : nullptr;
    if (!std::strcmp(name, "vkQueueSubmit")) return reinterpret_cast<PFN_vkVoidFunction>(submit1);
    if (!std::strcmp(name, "vkQueueSubmit2")) return reinterpret_cast<PFN_vkVoidFunction>(submit2_1);
    if (!std::strcmp(name, "vkQueueSubmit2KHR")) return nullptr;
    if (!std::strcmp(name, "device_special")) return reinterpret_cast<PFN_vkVoidFunction>(submit1);
    return device_proc0(device, name);
}
PFN_vkVoidFunction VKAPI_CALL instance_proc0(VkInstance, const char* name) {
    if (!std::strcmp(name, "vkCreateInstance")) return reinterpret_cast<PFN_vkVoidFunction>(instance_create0);
    if (!std::strcmp(name, "vkCreateDevice")) return reinterpret_cast<PFN_vkVoidFunction>(device_create);
    if (!std::strcmp(name, "vkDestroyInstance")) return reinterpret_cast<PFN_vkVoidFunction>(instance_destroy);
    if (!std::strcmp(name, "vkEnumerateDeviceExtensionProperties")) return reinterpret_cast<PFN_vkVoidFunction>(enumerate_extensions);
    if (!std::strcmp(name, "vkGetPhysicalDeviceFeatures2") || !std::strcmp(name, "vkGetPhysicalDeviceFeatures2KHR"))
        return line_mock[0].features2_available ? reinterpret_cast<PFN_vkVoidFunction>(features2) : nullptr;
    if (!std::strcmp(name, "vkGetPhysicalDeviceProperties2") || !std::strcmp(name, "vkGetPhysicalDeviceProperties2KHR"))
        return line_mock[0].properties2_available ? reinterpret_cast<PFN_vkVoidFunction>(properties2) : nullptr;
    return device_proc0(VK_NULL_HANDLE, name);
}
PFN_vkVoidFunction VKAPI_CALL instance_proc1(VkInstance instance, const char* name) {
    if (!std::strcmp(name, "vkCreateInstance")) return reinterpret_cast<PFN_vkVoidFunction>(instance_create1);
    if (!std::strcmp(name, "vkCreateDevice")) return reinterpret_cast<PFN_vkVoidFunction>(device_create);
    if (!std::strcmp(name, "vkDestroyInstance")) return reinterpret_cast<PFN_vkVoidFunction>(instance_destroy);
    if (!std::strcmp(name, "vkEnumerateDeviceExtensionProperties")) return reinterpret_cast<PFN_vkVoidFunction>(enumerate_extensions);
    if (!std::strcmp(name, "vkGetPhysicalDeviceFeatures2") || !std::strcmp(name, "vkGetPhysicalDeviceFeatures2KHR"))
        return line_mock[1].features2_available ? reinterpret_cast<PFN_vkVoidFunction>(features2) : nullptr;
    if (!std::strcmp(name, "vkGetPhysicalDeviceProperties2") || !std::strcmp(name, "vkGetPhysicalDeviceProperties2KHR"))
        return line_mock[1].properties2_available ? reinterpret_cast<PFN_vkVoidFunction>(properties2) : nullptr;
    return device_proc1(VK_NULL_HANDLE, name);
}

VkInstance make_instance(int id, uint32_t api = VK_API_VERSION_1_1, bool khr_features2 = false) {
    VkLayerInstanceLink next{nullptr, id ? instance_proc1 : instance_proc0, nullptr};
    VkLayerInstanceCreateInfo link{};
    link.sType = VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO; link.function = VK_LAYER_LINK_INFO; link.u.pLayerInfo = &next;
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO}; app.apiVersion = api;
    VkInstanceCreateInfo info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO}; info.pNext = &link; info.pApplicationInfo = &app;
    const char* extension = VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME;
    if (khr_features2) { info.enabledExtensionCount = 1; info.ppEnabledExtensionNames = &extension; }
    VkInstance instance{};
    auto create = reinterpret_cast<PFN_vkCreateInstance>(vispy_GetInstanceProcAddr(VK_NULL_HANDLE, "vkCreateInstance"));
    require(create(&info, nullptr, &instance) == VK_SUCCESS, "line test instance created");
    return instance;
}
VkResult make_device(VkInstance instance, int id, VkDevice& device, void* caller_feature = nullptr,
                     const std::vector<const char*>& caller_extensions = {}) {
    VkLayerDeviceLink next{nullptr, id ? instance_proc1 : instance_proc0, id ? device_proc1 : device_proc0};
    VkLayerDeviceCreateInfo link{};
    link.sType = VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO; link.function = VK_LAYER_LINK_INFO; link.u.pLayerInfo = &next;
    VkDeviceCreateInfo info{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO}; info.pNext = &link;
    if (caller_feature) {
        auto* base = reinterpret_cast<VkBaseOutStructure*>(caller_feature);
        base->pNext = reinterpret_cast<VkBaseOutStructure*>(&link);
        info.pNext = caller_feature;
    }
    info.enabledExtensionCount = static_cast<uint32_t>(caller_extensions.size()); info.ppEnabledExtensionNames = caller_extensions.data();
    const auto create = reinterpret_cast<PFN_vkCreateDevice>(vispy_GetInstanceProcAddr(instance, "vkCreateDevice"));
    auto result = create(reinterpret_cast<VkPhysicalDevice>(&physical_handles[id]), &info, nullptr, &device);
    if (caller_feature) {
        require(reinterpret_cast<VkBaseOutStructure*>(caller_feature)->pNext == reinterpret_cast<VkBaseOutStructure*>(&link), "caller feature chain not mutated");
        reinterpret_cast<VkBaseOutStructure*>(caller_feature)->pNext = nullptr;
    }
    return result;
}
void retire_device(VkDevice device) {
    reinterpret_cast<PFN_vkDestroyDevice>(vispy_GetDeviceProcAddr(device, "vkDestroyDevice"))(device, nullptr);
}
void retire_instance(VkInstance instance) {
    reinterpret_cast<PFN_vkDestroyInstance>(vispy_GetInstanceProcAddr(instance, "vkDestroyInstance"))(instance, nullptr);
}

VulkanMemoryTelemetry memory_snapshot() {
    VulkanMemoryTelemetry result;
    require(vispy_layer_vk_memory_snapshot(&result, sizeof(result)) == 1 && result.schema == 1,
            "coherent versioned memory snapshot");
    return result;
}
// BEGIN ADDED ACTUAL-HOOK WINDOW CONTRACTS (authored, unbuilt).
VulkanMemoryWindow window_begin() {
    VulkanMemoryWindow result;
    require(vispy_layer_vk_memory_window_begin(&result, sizeof(result)) == 1 && result.schema == 1,
            "actual layer window begin ABI");
    return result;
}
VulkanMemoryWindow window_end(uint64_t token) {
    VulkanMemoryWindow result;
    require(vispy_layer_vk_memory_window_end(token, &result, sizeof(result)) == 1 && result.schema == 1,
            "actual layer window end ABI");
    return result;
}
void memory_window_hook_contracts() {
    using Status = VulkanMemoryWindowStatus;
    static_assert(sizeof(VulkanMemoryTelemetry) == 19 * sizeof(uint64_t), "old snapshot ABI retained");
    const auto clean = memory_snapshot();
    require(!clean.active_devices && !clean.live_allocations && !clean.live_bytes && !clean.tracking_errors &&
            !clean.retired_allocations, "window hook fixtures start before terminal old-memory negatives");
    VulkanMemoryWindow untouched; untouched.schema = 99; untouched.token = 777;
    require(!vispy_layer_vk_memory_window_begin(nullptr, sizeof(untouched)) &&
            !vispy_layer_vk_memory_window_begin(&untouched, sizeof(untouched)-1) &&
            untouched.schema == 99 && untouched.token == 777, "malformed begin ABI never touches output or creates owner");
    auto absent = window_begin();
    require(absent.status == Status::Unavailable && absent.supported == 1 && !absent.available && !absent.token,
            "loaded layer with no actual devices is explicitly unavailable");
    require(window_end(0).status == Status::InvalidToken, "missing token does not create an owner");

    line_mock[0] = {}; line_mock[1] = {};
    memory_result[0] = VK_SUCCESS; memory_result[1] = VK_SUCCESS;
    memory_dispatch_available[0] = memory_dispatch_available[1] = true;
    memory_handle[0] = memory_handle[1] = 4000;
    auto instance0 = make_instance(0), instance1 = make_instance(1);
    VkDevice device0{}, device1{};
    require(make_device(instance0, 0, device0) == VK_SUCCESS && make_device(instance1, 1, device1) == VK_SUCCESS,
            "window hook devices created through actual intercepted dispatch");
    auto allocate = reinterpret_cast<PFN_vkAllocateMemory>(vispy_GetDeviceProcAddr(device0, "vkAllocateMemory"));
    auto allocate_instance = reinterpret_cast<PFN_vkAllocateMemory>(vispy_GetInstanceProcAddr(instance1, "vkAllocateMemory"));
    auto free = reinterpret_cast<PFN_vkFreeMemory>(vispy_GetDeviceProcAddr(device0, "vkFreeMemory"));
    auto free_instance = reinterpret_cast<PFN_vkFreeMemory>(vispy_GetInstanceProcAddr(instance1, "vkFreeMemory"));
    require(allocate && free && allocate == allocate_instance && free == free_instance,
            "both GIPA and GDPA route through actual identical memory hooks");
    VkMemoryAllocateFlagsInfo tail{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_FLAGS_INFO};
    VkMemoryAllocateInfo info{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    info.pNext = &tail; info.memoryTypeIndex = 3; info.allocationSize = 64;
    VkAllocationCallbacks callbacks{};
    expected_memory_info = &info; expected_memory_allocator = &callbacks; check_memory_forwarding = true;
    VkDeviceMemory memory0{}, memory1{}, temporary{};
    info.allocationSize = 4096;
    require(allocate(device0, &info, &callbacks, &temporary) == VK_SUCCESS, "larger cold allocation forwarded");
    free_instance(device0, temporary, &callbacks);
    // Reusing an already-freed fake handle is legal; synchronize the two fake
    // allocators so the seed checks still exercise colliding per-device IDs.
    memory_handle[0] = memory_handle[1] = 5000;
    info.allocationSize = 64;
    require(allocate(device0, &info, &callbacks, &memory0) == VK_SUCCESS, "cold seed allocation0 forwarded");
    info.allocationSize = 96;
    require(allocate_instance(device1, &info, &callbacks, &memory1) == VK_SUCCESS && memory0 == memory1,
            "same numerical handle on two devices remains separately owned");
    const auto before = memory_snapshot();
    require(before.peak_live_bytes >= 4096, "old lifetime peak retains larger freed cold allocation");
    auto begin = window_begin();
    require(begin.status == Status::Active && begin.token && begin.supported == 1 && begin.available == 1 && begin.complete == 1 &&
            begin.seed_live_allocations == 2 && begin.seed_live_bytes == 160 &&
            begin.counters.live_allocations == 2 && begin.counters.live_bytes == 160 &&
            begin.counters.peak_live_bytes == 160 && !begin.counters.allocate_calls && !begin.counters.free_calls,
            "begin seeds actual current ownership and excludes cold events");
    auto overlap = window_begin();
    require(overlap.status == Status::Overlap && !overlap.token, "overlapping begin cannot replace active owner");
    require(window_end(0).status == Status::InvalidToken && window_end(begin.token+1).status == Status::InvalidToken,
            "missing and foreign tokens cannot consume owner");
    require(!vispy_layer_vk_memory_window_end(begin.token, nullptr, sizeof(untouched)) &&
            !vispy_layer_vk_memory_window_end(begin.token, &untouched, sizeof(untouched)-1) &&
            untouched.schema == 99 && untouched.token == 777, "malformed end ABI cannot consume owner or touch output");

    // No lifetime/window snapshot occurs between this allocation and free.
    info.allocationSize = 512;
    require(allocate_instance(device0, &info, &callbacks, &temporary) == VK_SUCCESS,
            "short-lived allocation reaches actual layer hook and fake downstream");
    free_instance(device0, temporary, &callbacks);
    memory_result[1] = VK_ERROR_OUT_OF_DEVICE_MEMORY;
    VkDeviceMemory stale = memory1;
    require(allocate(device1, &info, &callbacks, &stale) == VK_ERROR_OUT_OF_DEVICE_MEMORY && stale == memory1,
            "failed allocation preserves downstream result and stale output");
    memory_result[1] = VK_SUCCESS;
    free(device0, VK_NULL_HANDLE, &callbacks);
    auto end = window_end(begin.token);
    const auto& c = end.counters;
    require(end.token == begin.token && end.status == Status::Complete && end.available == 1 && end.complete == 1 && !end.invalidations &&
            end.seed_live_allocations == 2 && end.seed_live_bytes == 160 &&
            c.allocate_calls == 2 && c.allocate_failures == 1 && c.allocation_count == 1 && c.allocated_bytes == 512 &&
            c.free_calls == 2 && c.free_count == 1 && c.freed_bytes == 512 && c.null_free_calls == 1 &&
            c.live_allocations == 2 && c.live_bytes == 160 && c.peak_live_allocations == 3 && c.peak_live_bytes == 672 &&
            c.peak_live_bytes < before.peak_live_bytes &&
            !c.unknown_free_calls && !c.retired_allocations && !c.tracking_errors,
            "actual-hook window keeps inter-boundary event peak and exact successful/failed/null deltas");
    const auto after = memory_snapshot();
    require(after.live_bytes == before.live_bytes && after.live_allocations == before.live_allocations &&
            after.allocate_calls-before.allocate_calls == c.allocate_calls &&
            after.allocated_bytes-before.allocated_bytes == c.allocated_bytes &&
            after.free_count-before.free_count == c.free_count && after.freed_bytes-before.freed_bytes == c.freed_bytes,
            "window deltas conserve actual unchanged boundary ownership without resetting old counters");
    require(window_end(begin.token).status == Status::InvalidToken, "completed token is stale");

    auto loss = window_begin();
    require(loss.status == Status::Active && loss.token > begin.token, "window tokens advance after closure");
    memory_result[1] = VK_ERROR_DEVICE_LOST;
    stale = memory1;
    require(allocate_instance(device1, &info, &callbacks, &stale) == VK_ERROR_DEVICE_LOST && stale == memory1,
            "actual failed allocation device-loss result is unchanged");
    auto lost = window_end(loss.token);
    require(lost.status == Status::Incomplete && !lost.complete && (lost.invalidations & WindowDeviceLost) &&
            lost.counters.allocate_calls == 1 && lost.counters.allocate_failures == 1 &&
            !lost.counters.allocation_count && !lost.counters.allocated_bytes && lost.counters.live_bytes == 160,
            "device-loss allocation invalidates window without fabricating ownership or frees");
    memory_result[1] = VK_SUCCESS;

    auto first_free = window_begin();
    require(first_free.status == Status::Active && first_free.seed_live_bytes == 160, "post-negative raw layer fixture begins next window");
    free_instance(device0, memory0, &callbacks);
    auto one = window_end(first_free.token);
    require(one.status == Status::Complete && one.counters.live_allocations == 1 && one.counters.live_bytes == 96 &&
            one.counters.free_count == 1 && one.counters.freed_bytes == 64 && one.counters.peak_live_bytes == 160,
            "freeing same-value device0 handle leaves device1 handle intact");
    auto second_free = window_begin();
    require(second_free.status == Status::Active && second_free.seed_live_bytes == 96, "next window seeds remaining device ownership");
    free(device1, memory1, &callbacks);
    auto none = window_end(second_free.token);
    require(none.status == Status::Complete && !none.counters.live_allocations && !none.counters.live_bytes &&
            none.counters.free_count == 1 && none.counters.freed_bytes == 96 && none.counters.peak_live_bytes == 96,
            "second device same-value handle is freed independently");

    auto terminal = window_begin();
    require(terminal.status == Status::Active && !terminal.seed_live_bytes, "terminal negative window begins clean");
    info.allocationSize = 23;
    require(allocate(device0, &info, &callbacks, &temporary) == VK_SUCCESS, "window retirement allocation forwarded");
    free_instance(device1, reinterpret_cast<VkDeviceMemory>(999999), &callbacks);
    retire_device(device0);
    auto retired = window_end(terminal.token);
    require(retired.status == Status::Incomplete && !retired.complete && retired.available == 1 &&
            (retired.invalidations & WindowTrackingError) && (retired.invalidations & WindowDeviceRetired) &&
            retired.counters.allocation_count == 1 && retired.counters.allocated_bytes == 23 &&
            retired.counters.free_calls == 1 && retired.counters.unknown_free_calls == 1 && retired.counters.tracking_errors == 1 &&
            !retired.counters.free_count && !retired.counters.freed_bytes &&
            retired.counters.retired_allocations == 1 && retired.counters.retired_bytes == 23 &&
            !retired.counters.live_allocations && !retired.counters.live_bytes && retired.counters.peak_live_bytes == 23,
            "actual unknown-free and device-retirement paths invalidate without invented explicit frees");
    auto poisoned = window_begin();
    require(poisoned.status == Status::Incomplete && !poisoned.token, "incomplete prior ownership cannot seed a later complete window");
    retire_device(device1);
    check_memory_forwarding = false;
    memory_dispatch_available[1] = false;
    require(make_device(instance1, 1, device1) == VK_SUCCESS, "older device path remains usable without memory dispatch");
    auto unsupported = window_begin();
    require(unsupported.status == Status::Unavailable && unsupported.supported == 1 && !unsupported.available && !unsupported.token,
            "missing memory dispatch is unavailable rather than a measured zero peak");
    retire_device(device1); memory_dispatch_available[1] = true;
    retire_instance(instance0); retire_instance(instance1);
    require(!memory_snapshot().active_devices && !memory_snapshot().live_bytes, "window hook fixtures retire all owned devices/records");
    // Restore only the fake driver's unused handle-number generator. All layer
    // lifetime counters remain untouched; old tests retain their own baselines.
    memory_handle[0] = memory_handle[1] = 1000;
    expected_memory_info = nullptr; expected_memory_allocator = nullptr;
    std::cout << "Event-level allocation-window actual-hook contract assertions passed\n";
}
// END ADDED ACTUAL-HOOK WINDOW CONTRACTS.

void memory_contracts() {
    const auto baseline = memory_snapshot();
    require(!baseline.live_allocations && !baseline.live_bytes, "memory starts with no stale allocations");
    require(!vispy_layer_vk_memory_snapshot(nullptr, sizeof(baseline)) &&
            !vispy_layer_vk_memory_snapshot(const_cast<VulkanMemoryTelemetry*>(&baseline), sizeof(baseline) - 1),
            "invalid memory snapshot ABI is rejected without access");
    line_mock[0] = {}; line_mock[1] = {};
    auto instance0 = make_instance(0), instance1 = make_instance(1);
    VkDevice device0{}, device1{};
    require(make_device(instance0, 0, device0) == VK_SUCCESS && make_device(instance1, 1, device1) == VK_SUCCESS,
            "memory devices created independently");
    auto tracked = memory_snapshot();
    require(tracked.active_devices == 2 && tracked.tracking_devices == 2, "tracking dispatch capability reflects actual devices");
    auto allocate = reinterpret_cast<PFN_vkAllocateMemory>(vispy_GetDeviceProcAddr(device0, "vkAllocateMemory"));
    auto free = reinterpret_cast<PFN_vkFreeMemory>(vispy_GetInstanceProcAddr(instance1, "vkFreeMemory"));
    require(allocate && free, "both device and instance lookup intercept memory APIs");
    VkMemoryAllocateFlagsInfo tail{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_FLAGS_INFO};
    VkMemoryAllocateInfo info{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    info.pNext = &tail; info.allocationSize = 64; info.memoryTypeIndex = 3;
    VkAllocationCallbacks callbacks{};
    expected_memory_info = &info; expected_memory_allocator = &callbacks; check_memory_forwarding = true;
    VkDeviceMemory memory0{}, memory1{};
    require(allocate(device0, &info, &callbacks, &memory0) == VK_SUCCESS, "first actual memory allocation");
    info.allocationSize = 96;
    require(allocate(device1, &info, &callbacks, &memory1) == VK_SUCCESS && memory0 == memory1,
            "colliding non-dispatchable handles retain distinct device ownership");
    auto both = memory_snapshot();
    require(both.allocation_count - baseline.allocation_count == 2 && both.allocated_bytes - baseline.allocated_bytes == 160 &&
            both.live_allocations == 2 && both.live_bytes == 160 && both.peak_live_bytes >= 160,
            "actual allocation sizes and aggregate live/peak counters");
    memory_result[1] = VK_ERROR_OUT_OF_DEVICE_MEMORY;
    VkDeviceMemory stale_output = memory1;
    require(allocate(device1, &info, &callbacks, &stale_output) == VK_ERROR_OUT_OF_DEVICE_MEMORY && stale_output == memory1,
            "failed native allocation result and stale output preserved");
    auto failed = memory_snapshot();
    require(failed.allocate_calls - baseline.allocate_calls == 3 && failed.allocate_failures - baseline.allocate_failures == 1 &&
            failed.live_bytes == 160 && failed.allocation_count == both.allocation_count,
            "failed allocations add no fabricated live memory");
    memory_result[1] = VK_SUCCESS;
    free(device0, memory0, &callbacks);
    free(device0, VK_NULL_HANDLE, &callbacks);
    auto one = memory_snapshot();
    require(one.live_allocations == 1 && one.live_bytes == 96 && one.free_count - baseline.free_count == 1 &&
            one.freed_bytes - baseline.freed_bytes == 64 && one.null_free_calls - baseline.null_free_calls == 1,
            "null free forwards without releasing another device's handle");
    free(device1, memory1, &callbacks);
    check_memory_forwarding = false;
    std::atomic<bool> concurrent_ok{true};
    auto churn = [&](VkDevice device) {
        VkMemoryAllocateInfo local{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO}; local.allocationSize = 17;
        for (int i = 0; i < 500; ++i) {
            VkDeviceMemory memory{};
            if (allocate(device, &local, nullptr, &memory) != VK_SUCCESS) concurrent_ok = false;
            auto snapshot = memory_snapshot();
            if (snapshot.allocated_bytes - snapshot.freed_bytes - snapshot.retired_bytes != snapshot.live_bytes)
                concurrent_ok = false;
            free(device, memory, nullptr);
        }
    };
    std::thread first([&] { churn(device0); }), second([&] { churn(device1); });
    first.join(); second.join();
    auto settled = memory_snapshot();
    require(concurrent_ok && !settled.live_bytes && !settled.live_allocations &&
            settled.allocation_count - baseline.allocation_count == 1002 && settled.free_count - baseline.free_count == 1002 &&
            settled.tracking_errors == baseline.tracking_errors,
            "concurrent allocation/free snapshots retain exact accounting");
    // Simulate an unobserved handle and a leftover record at device retirement.
    // Neither event is presented as an observed successful explicit free.
    free(device1, reinterpret_cast<VkDeviceMemory>(999999), nullptr);
    info.allocationSize = 23;
    require(allocate(device0, &info, nullptr, &memory0) == VK_SUCCESS, "retirement record created");
    auto before_destroy = memory_snapshot();
    retire_device(device0); retire_device(device1);
    auto retired = memory_snapshot();
    require(!retired.active_devices && !retired.tracking_devices && !retired.live_allocations && !retired.live_bytes &&
            retired.retired_allocations - baseline.retired_allocations == 1 && retired.retired_bytes - baseline.retired_bytes == 23 &&
            retired.free_count == before_destroy.free_count && retired.unknown_free_calls - baseline.unknown_free_calls == 1 &&
            retired.tracking_errors - baseline.tracking_errors == 1,
            "unknown and device-retired records remain explicit, never fabricated frees");
    require(allocate(device0, &info, nullptr, &memory0) == VK_ERROR_DEVICE_LOST,
            "retired device cannot address stale allocation dispatch");
    memory_dispatch_available[1] = false;
    require(make_device(instance1, 1, device1) == VK_SUCCESS, "device without memory dispatch still created");
    auto unavailable = memory_snapshot();
    require(unavailable.active_devices == 1 && !unavailable.tracking_devices &&
            !vispy_GetDeviceProcAddr(device1, "vkAllocateMemory") && !vispy_GetInstanceProcAddr(instance1, "vkFreeMemory"),
            "missing next-layer functions cannot claim memory interception capability");
    retire_device(device1); memory_dispatch_available[1] = true;
    retire_instance(instance0); retire_instance(instance1);
}

void line_contracts() {
    line_mock[0] = {}; line_mock[1] = {};
    line_mock[0].supported_extensions = {VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME, VK_KHR_LINE_RASTERIZATION_EXTENSION_NAME};
    line_mock[1].supported_extensions = {VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME};
    auto instance0 = make_instance(0), instance1 = make_instance(1);
    VkDevice device0{}, device1{};
    const uint64_t device_creations_before = vispy_layer_vk_bresenham_device_creations();
    vispy_layer_vk_enable_bresenham(0);
    require(make_device(instance0, 0, device0) == VK_SUCCESS && !vispy_layer_vk_bresenham_device_count() && !line_mock[0].queries,
            "default counting-only policy does not query or augment device features");
    require(vispy_layer_vk_bresenham_device_creations() == device_creations_before, "counting-only device cannot claim a Bresenham creation");
    retire_device(device0);
    vispy_layer_vk_enable_bresenham(1);
    line_mock[0].incomplete = 1;
    VkPhysicalDeviceFeatures2 original{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2}; original.features.samplerAnisotropy = VK_TRUE;
    require(make_device(instance0, 0, device0, &original, {"caller_extension"}) == VK_SUCCESS, "supported KHR device created");
    require(original.features.samplerAnisotropy && line_mock[0].enabled && line_mock[0].feature_structs == 1 &&
            line_mock[0].next_after_line == &original && line_mock[0].enabled_extensions ==
            std::vector<std::string>{"caller_extension", VK_KHR_LINE_RASTERIZATION_EXTENSION_NAME}, "KHR feature prepended while caller data and extensions survive");
    require(make_device(instance1, 1, device1) == VK_SUCCESS && line_mock[1].enabled_extensions ==
            std::vector<std::string>{VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME} && vispy_layer_vk_bresenham_device_count() == 2,
            "EXT fallback and per-device capability independent");
    require(vispy_layer_vk_bresenham_device_creations() == device_creations_before + 2,
            "only successful queried-enabled device creations counted cumulatively");

    VkPipelineInputAssemblyStateCreateInfo assembly[3]{};
    VkPipelineRasterizationStateCreateInfo raster[3]{};
    VkGraphicsPipelineCreateInfo info[3]{};
    VkPipelineRasterizationDepthClipStateCreateInfoEXT tail{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_DEPTH_CLIP_STATE_CREATE_INFO_EXT};
    for (int i = 0; i < 3; ++i) {
        assembly[i].sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
        assembly[i].topology = i == 1 ? VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST : i == 0 ? VK_PRIMITIVE_TOPOLOGY_LINE_LIST : VK_PRIMITIVE_TOPOLOGY_LINE_STRIP;
        raster[i].sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO; raster[i].lineWidth = 1;
        raster[i].pNext = &tail; raster[i].cullMode = VK_CULL_MODE_BACK_BIT;
        info[i].sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO; info[i].pInputAssemblyState = &assembly[i]; info[i].pRasterizationState = &raster[i];
    }
    auto create = reinterpret_cast<PFN_vkCreateGraphicsPipelines>(vispy_GetDeviceProcAddr(device0, "vkCreateGraphicsPipelines"));
    require(create && vispy_GetInstanceProcAddr(instance0, "vkCreateGraphicsPipelines") == reinterpret_cast<PFN_vkVoidFunction>(create), "GIPA and GDPA retain pipeline interception");
    const uint64_t before = vispy_layer_vk_bresenham_pipeline_count();
    VkPipeline outputs[3]{}; expected_graphics = info;
    require(create(device0, VK_NULL_HANDLE, 3, info, nullptr, outputs) == VK_SUCCESS && selected_lines == std::vector<bool>{true, false, true},
            "mixed batches affect only list/strip line pipelines");
    require(!graphics_unchanged && selected_raster[1] == &raster[1] && selected_line_tail[0] == &tail && selected_line_tail[2] == &tail &&
            raster[0].pNext == &tail && raster[0].cullMode == VK_CULL_MODE_BACK_BIT && vispy_layer_vk_bresenham_pipeline_count() == before + 2,
            "caller raster chains remain unchanged and only successful line creations count");
    expected_graphics = &info[1];
    require(create(device0, VK_NULL_HANDLE, 1, &info[1], nullptr, outputs) == VK_SUCCESS && graphics_unchanged, "triangle-only batch is forwarded verbatim");
    VkPipelineRasterizationLineStateCreateInfoKHR explicit_line{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_LINE_STATE_CREATE_INFO_KHR};
    explicit_line.lineRasterizationMode = VK_LINE_RASTERIZATION_MODE_RECTANGULAR_KHR;
    raster[0].pNext = &explicit_line; expected_graphics = info;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && graphics_unchanged && !selected_lines[0], "caller explicit line mode is preserved");
    raster[0].pNext = &tail;
    VkDynamicState mode = VK_DYNAMIC_STATE_LINE_RASTERIZATION_MODE_EXT;
    VkPipelineDynamicStateCreateInfo dynamic{VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO}; dynamic.dynamicStateCount = 1; dynamic.pDynamicStates = &mode;
    info[0].pDynamicState = &dynamic;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && graphics_unchanged, "dynamic line policy not overridden");
    mode = VK_DYNAMIC_STATE_LINE_WIDTH;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && selected_lines[0] &&
            vispy_layer_vk_bresenham_pipeline_count() == before + 3,
            "pinned Dawn dynamic width1 keeps queried Bresenham line policy");
    mode = VK_DYNAMIC_STATE_PRIMITIVE_TOPOLOGY;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && graphics_unchanged,
            "dynamic topology is not guessed from its ignored static descriptor");
    info[0].pDynamicState = nullptr; raster[0].lineWidth = 2;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && graphics_unchanged, "wide line policy not silently changed");
    raster[0].lineWidth = 1; graphics_result = VK_ERROR_DEVICE_LOST;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_ERROR_DEVICE_LOST && vispy_layer_vk_bresenham_pipeline_count() == before + 3,
            "native pipeline errors forwarded without fabricated successful creations");
    graphics_result = VK_SUCCESS;

    retire_device(device1); line_mock[1].supported = false;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !line_mock[1].enabled && line_mock[1].enabled_extensions.empty() &&
            vispy_layer_vk_bresenham_device_count() == 1, "advertised extension without feature stays unsupported");
    require(create(device1, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && graphics_unchanged, "unsupported device retains native pipelines");
    retire_device(device1); line_mock[1].supported = true;
    VkPhysicalDeviceLineRasterizationFeaturesEXT caller_line{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_EXT};
    require(make_device(instance1, 1, device1, &caller_line) == VK_SUCCESS && !line_mock[1].enabled && line_mock[1].feature_structs == 1 &&
            vispy_layer_vk_bresenham_device_count() == 1, "caller disabled feature is never overridden or duplicated");
    retire_device(device1); caller_line.bresenhamLines = VK_TRUE;
    require(make_device(instance1, 1, device1, &caller_line, {VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME}) == VK_SUCCESS &&
            line_mock[1].feature_structs == 1 && line_mock[1].enabled_extensions.size() == 1 && vispy_layer_vk_bresenham_device_count() == 2,
            "caller enabled feature and extension reused without duplication");
    retire_device(device1);
    VkPhysicalDeviceVulkan14Features aggregate{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_4_FEATURES};
    require(make_device(instance1, 1, device1, &aggregate) == VK_SUCCESS && !line_mock[1].feature_structs &&
            vispy_layer_vk_bresenham_device_count() == 1, "promoted caller aggregate cannot be contradicted by duplicate feature alias");
    retire_device(device1); line_mock[1].enumeration_failure = true;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && vispy_layer_vk_bresenham_device_count() == 1, "query failure leaves native device policy unchanged");
    retire_device(device1); line_mock[1].enumeration_failure = false; line_mock[1].supported_extensions.clear();
    const unsigned no_extension_queries = line_mock[1].queries;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && line_mock[1].queries == no_extension_queries &&
            line_mock[1].enabled_extensions.empty() && !line_mock[1].feature_structs && vispy_layer_vk_bresenham_device_count() == 1,
            "unadvertised extension never queried or enabled");
    retire_device(device1); line_mock[1].supported_extensions = {VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME}; line_mock[1].device_failure = true;
    const uint64_t failed_before = vispy_layer_vk_bresenham_device_creations();
    require(make_device(instance1, 1, device1) == VK_ERROR_FEATURE_NOT_PRESENT && !device1 && vispy_layer_vk_active_device_count() == 1 &&
            vispy_layer_vk_bresenham_device_creations() == failed_before,
            "native device creation error does not publish dispatch/capability");
    line_mock[1].device_failure = false;
    retire_instance(instance1); instance1 = make_instance(1, VK_API_VERSION_1_0);
    const unsigned queries = line_mock[1].queries;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && line_mock[1].queries == queries && vispy_layer_vk_bresenham_device_count() == 1,
            "Features2 unavailable without1.1 or enabled KHR instance extension");
    retire_device(device1); retire_instance(instance1); instance1 = make_instance(1, VK_API_VERSION_1_0, true);
    require(make_device(instance1, 1, device1) == VK_SUCCESS && line_mock[1].queries > queries && vispy_layer_vk_bresenham_device_count() == 2,
            "KHR Features2 works only when instance extension enabled");
    retire_device(device1); retire_device(device0); retire_instance(instance1); retire_instance(instance0);
    vispy_layer_vk_enable_bresenham(0);
    require(!vispy_layer_vk_active_instance_count() && !vispy_layer_vk_active_device_count() && !vispy_layer_vk_bresenham_device_count(), "line capability retires with owning devices");
}

void last_vertex_contracts() {
    line_mock[0] = {}; line_mock[1] = {};
    line_mock[0].supported_extensions = {VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME, VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME};
    line_mock[1].supported_extensions = {VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME};
    auto instance0 = make_instance(0), instance1 = make_instance(1);
    VkDevice device0{}, device1{};
    const uint64_t initial_creations = vispy_layer_vk_last_vertex_device_creations();
    vispy_layer_vk_enable_bresenham(0); vispy_layer_vk_enable_last_vertex(0);
    require(make_device(instance0, 0, device0) == VK_SUCCESS && !line_mock[0].last_queries &&
            !line_mock[0].properties_queries && !line_mock[0].last_feature_structs &&
            vispy_layer_vk_last_vertex_device_creations() == initial_creations,
            "LAST policy is independently off by default without feature/property queries");
    retire_device(device0);
    vispy_layer_vk_enable_last_vertex(1);
    line_mock[0].incomplete = 1;
    VkPhysicalDeviceFeatures2 original{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2};
    original.features.samplerAnisotropy = VK_TRUE;
    require(make_device(instance0, 0, device0, &original, {"caller_extension"}) == VK_SUCCESS &&
            line_mock[0].last_enabled && line_mock[0].last_feature_structs == 1 && !line_mock[0].feature_structs &&
            line_mock[0].next_after_last == &original && original.features.samplerAnisotropy == VK_TRUE &&
            line_mock[0].enabled_extensions == std::vector<std::string>{"caller_extension", VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME} &&
            vispy_layer_vk_last_vertex_device_creations() == initial_creations + 1 && !vispy_layer_vk_bresenham_device_count(),
            "advertised queried feature and per-pipeline property enable LAST without changing caller data or Bresenham policy");
    line_mock[1].last_supported = false;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !line_mock[1].last_enabled &&
            line_mock[1].enabled_extensions.empty() && !line_mock[1].properties_queries &&
            vispy_layer_vk_last_vertex_device_creations() == initial_creations + 1,
            "advertised extension without provokingVertexLast cannot claim capability");

    VkPipelineInputAssemblyStateCreateInfo assembly[3]{};
    VkPipelineRasterizationStateCreateInfo raster[3]{};
    VkGraphicsPipelineCreateInfo info[3]{};
    VkPipelineRasterizationDepthClipStateCreateInfoEXT tail{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_DEPTH_CLIP_STATE_CREATE_INFO_EXT};
    const VkPrimitiveTopology topologies[] = {VK_PRIMITIVE_TOPOLOGY_LINE_LIST, VK_PRIMITIVE_TOPOLOGY_TRIANGLE_STRIP, VK_PRIMITIVE_TOPOLOGY_POINT_LIST};
    for (int i = 0; i < 3; ++i) {
        assembly[i].sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO; assembly[i].topology = topologies[i];
        raster[i].sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
        raster[i].lineWidth = 1; raster[i].pNext = &tail; raster[i].cullMode = VK_CULL_MODE_BACK_BIT;
        info[i].sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
        info[i].pInputAssemblyState = &assembly[i]; info[i].pRasterizationState = &raster[i];
    }
    auto create = reinterpret_cast<PFN_vkCreateGraphicsPipelines>(vispy_GetDeviceProcAddr(device0, "vkCreateGraphicsPipelines"));
    const uint64_t pipeline_start = vispy_layer_vk_last_vertex_pipeline_count();
    VkPipeline outputs[3]{}; expected_graphics = info;
    require(create(device0, VK_NULL_HANDLE, 3, info, nullptr, outputs) == VK_SUCCESS &&
            selected_last == std::vector<bool>{true, true, true} && selected_lines == std::vector<bool>{false, false, false} &&
            provoking_nodes == std::vector<unsigned>{1, 1, 1} && selected_last_tail == std::vector<const void*>{&tail, &tail, &tail} &&
            raster[0].pNext == &tail && raster[1].pNext == &tail && raster[2].pNext == &tail &&
            raster[1].cullMode == VK_CULL_MODE_BACK_BIT && vispy_layer_vk_last_vertex_pipeline_count() == pipeline_start + 3,
            "LAST coherently applies to default point/line/triangle raster states without mutating caller chains");
    vispy_layer_vk_enable_last_vertex(0);
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && selected_last[0],
            "existing admitted device retains its policy after another device opt-in is disabled");
    require(create(device1, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && graphics_unchanged && !selected_last[0],
            "another device never inherits the admitted device policy");
    vispy_layer_vk_enable_last_vertex(1);

    VkPipelineRasterizationProvokingVertexStateCreateInfoEXT explicit_mode{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_PROVOKING_VERTEX_STATE_CREATE_INFO_EXT};
    explicit_mode.provokingVertexMode = VK_PROVOKING_VERTEX_MODE_FIRST_VERTEX_EXT; explicit_mode.pNext = &tail;
    raster[0].pNext = &explicit_mode;
    const uint64_t explicit_before = vispy_layer_vk_last_vertex_pipeline_count();
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && graphics_unchanged &&
            !selected_last[0] && provoking_nodes[0] == 1 && explicit_mode.pNext == &tail,
            "caller explicit FIRST mode is forwarded intact");
    explicit_mode.provokingVertexMode = VK_PROVOKING_VERTEX_MODE_LAST_VERTEX_EXT;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && graphics_unchanged &&
            selected_last[0] && provoking_nodes[0] == 1 && vispy_layer_vk_last_vertex_pipeline_count() == explicit_before,
            "caller explicit LAST is neither duplicated nor counted as policy interception");
    raster[0].pNext = &tail;
    VkDynamicState mode = VK_DYNAMIC_STATE_PROVOKING_VERTEX_MODE_EXT;
    VkPipelineDynamicStateCreateInfo dynamic{VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO};
    dynamic.dynamicStateCount = 1; dynamic.pDynamicStates = &mode; info[0].pDynamicState = &dynamic;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && graphics_unchanged && !selected_last[0],
            "dynamic provoking vertex mode is preserved");
    info[0].pDynamicState = nullptr;
    graphics_result = VK_ERROR_DEVICE_LOST;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_ERROR_DEVICE_LOST &&
            vispy_layer_vk_last_vertex_pipeline_count() == explicit_before,
            "failed native pipelines never fabricate successful LAST policy creations");
    graphics_result = VK_SUCCESS;

    // Admission failures must leave the downstream device/extension contract
    // intact and never advance the successful selected-device counter.
    retire_device(device1); line_mock[1].last_supported = true; line_mock[1].per_pipeline = false;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !line_mock[1].last_enabled &&
            line_mock[1].enabled_extensions.empty() && vispy_layer_vk_last_vertex_device_creations() == initial_creations + 1,
            "feature support without per-pipeline mode support is explicitly unadmitted");
    retire_device(device1); line_mock[1].per_pipeline = true;
    VkPhysicalDeviceProvokingVertexFeaturesEXT caller{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROVOKING_VERTEX_FEATURES_EXT};
    require(make_device(instance1, 1, device1, &caller) == VK_SUCCESS && !line_mock[1].last_enabled &&
            line_mock[1].last_feature_structs == 1 && caller.provokingVertexLast == VK_FALSE &&
            vispy_layer_vk_last_vertex_device_creations() == initial_creations + 1,
            "explicitly disabled caller feature is never enabled or duplicated");
    retire_device(device1); caller.provokingVertexLast = VK_TRUE;
    require(make_device(instance1, 1, device1, &caller, {VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME}) == VK_SUCCESS &&
            line_mock[1].last_enabled && line_mock[1].last_feature_structs == 1 && line_mock[1].enabled_extensions.size() == 1 &&
            caller.provokingVertexLast == VK_TRUE && vispy_layer_vk_last_vertex_device_creations() == initial_creations + 2,
            "enabled caller feature/extension is reused without changing its chain");
    retire_device(device1); line_mock[1].supported_extensions.clear();
    const unsigned unadvertised_queries = line_mock[1].last_queries;
    const uint64_t rejected_start = vispy_layer_vk_last_vertex_device_creations();
    require(make_device(instance1, 1, device1) == VK_SUCCESS && line_mock[1].last_queries == unadvertised_queries &&
            !line_mock[1].last_feature_structs && line_mock[1].enabled_extensions.empty() &&
            vispy_layer_vk_last_vertex_device_creations() == rejected_start, "unadvertised provoking extension is never queried or enabled");
    retire_device(device1); line_mock[1].supported_extensions = {VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME};
    line_mock[1].enumeration_failure = true;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !line_mock[1].last_enabled &&
            vispy_layer_vk_last_vertex_device_creations() == rejected_start, "extension query failure cannot fabricate LAST support");
    retire_device(device1); line_mock[1].enumeration_failure = false; line_mock[1].write_last_features = false;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !line_mock[1].last_enabled &&
            vispy_layer_vk_last_vertex_device_creations() == rejected_start, "unwritten feature query result remains unsupported");
    retire_device(device1); line_mock[1].write_last_features = true; line_mock[1].write_last_properties = false;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !line_mock[1].last_enabled &&
            vispy_layer_vk_last_vertex_device_creations() == rejected_start, "unwritten property query result remains unsupported");
    retire_device(device1); line_mock[1].write_last_properties = true; line_mock[1].device_failure = true;
    require(make_device(instance1, 1, device1) == VK_ERROR_FEATURE_NOT_PRESENT && !device1 &&
            vispy_layer_vk_active_device_count() == 1 && vispy_layer_vk_last_vertex_device_creations() == rejected_start,
            "failed native device creation does not publish dispatch or cumulative LAST capability");
    line_mock[1].device_failure = false; line_mock[1].graphics_available = false;
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !vispy_GetDeviceProcAddr(device1, "vkCreateGraphicsPipelines") &&
            vispy_layer_vk_last_vertex_device_creations() == rejected_start, "missing graphics interception dispatch cannot claim LAST support");
    retire_device(device1); line_mock[1].graphics_available = true;
    retire_instance(instance1); line_mock[1].properties2_available = false; instance1 = make_instance(1);
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !line_mock[1].last_enabled &&
            vispy_layer_vk_last_vertex_device_creations() == rejected_start, "Properties2 availability is independently required");
    retire_device(device1); retire_instance(instance1); line_mock[1].properties2_available = true;
    line_mock[1].features2_available = false; instance1 = make_instance(1);
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !line_mock[1].last_enabled &&
            vispy_layer_vk_last_vertex_device_creations() == rejected_start, "Features2 availability is independently required");
    retire_device(device1); retire_instance(instance1); line_mock[1].features2_available = true;
    instance1 = make_instance(1, VK_API_VERSION_1_0);
    require(make_device(instance1, 1, device1) == VK_SUCCESS && !line_mock[1].last_enabled &&
            vispy_layer_vk_last_vertex_device_creations() == rejected_start, "1.0 cannot use undeclared Features2/Properties2 functions");
    retire_device(device1); retire_instance(instance1); instance1 = make_instance(1, VK_API_VERSION_1_0, true);
    require(make_device(instance1, 1, device1) == VK_SUCCESS && line_mock[1].last_enabled &&
            vispy_layer_vk_last_vertex_device_creations() == rejected_start + 1,
            "enabled KHR instance extension admits both feature and property aliases on1.0");
    retire_device(device1); retire_instance(instance1);

    // Both opt-ins compose their feature and raster chains. LAST changes flat
    // semantics for every default topology; Bresenham stays limited to1px lines.
    retire_device(device0); vispy_layer_vk_enable_bresenham(1);
    const auto mixed_last_start = vispy_layer_vk_last_vertex_device_creations();
    const auto mixed_line_start = vispy_layer_vk_bresenham_device_creations();
    require(make_device(instance0, 0, device0, &original, {"caller_extension"}) == VK_SUCCESS &&
            line_mock[0].last_enabled && line_mock[0].enabled && line_mock[0].last_feature_structs == 1 && line_mock[0].feature_structs == 1 &&
            line_mock[0].feature_chain[0] == VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROVOKING_VERTEX_FEATURES_EXT &&
            line_mock[0].feature_chain[1] == VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_KHR &&
            line_mock[0].next_after_line == &original && original.features.samplerAnisotropy == VK_TRUE &&
            line_mock[0].enabled_extensions == std::vector<std::string>{"caller_extension", VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME, VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME} &&
            vispy_layer_vk_last_vertex_device_creations() == mixed_last_start + 1 &&
            vispy_layer_vk_bresenham_device_creations() == mixed_line_start + 1,
            "independent queried feature/extension chains compose while preserving original caller data");
    const auto mixed_last_pipelines = vispy_layer_vk_last_vertex_pipeline_count();
    const auto mixed_line_pipelines = vispy_layer_vk_bresenham_pipeline_count();
    require(create(device0, VK_NULL_HANDLE, 3, info, nullptr, outputs) == VK_SUCCESS &&
            selected_last == std::vector<bool>{true, true, true} && selected_lines == std::vector<bool>{true, false, false} &&
            last_precedes_line[0] && selected_line_tail[0] == &tail && selected_last_tail[1] == &tail &&
            provoking_nodes == std::vector<unsigned>{1, 1, 1} && raster[0].pNext == &tail &&
            vispy_layer_vk_last_vertex_pipeline_count() == mixed_last_pipelines + 3 &&
            vispy_layer_vk_bresenham_pipeline_count() == mixed_line_pipelines + 1,
            "mixed pipelines compose LAST then Bresenham then the unmodified caller raster tail");
    explicit_mode.provokingVertexMode = VK_PROVOKING_VERTEX_MODE_FIRST_VERTEX_EXT; raster[0].pNext = &explicit_mode;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && selected_lines[0] &&
            !selected_last[0] && provoking_nodes[0] == 1 && selected_line_tail[0] == &explicit_mode &&
            explicit_mode.pNext == &tail && vispy_layer_vk_last_vertex_pipeline_count() == mixed_last_pipelines + 3,
            "Bresenham composes with explicit provoking state without overriding or recounting it");
    raster[0].pNext = &tail; info[0].pDynamicState = &dynamic;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && selected_lines[0] && !selected_last[0],
            "dynamic provoking policy remains independent of static Bresenham line policy");
    info[0].pDynamicState = nullptr; raster[0].lineWidth = 2;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && !selected_lines[0] && selected_last[0] &&
            raster[0].lineWidth == 2, "wide lines retain their original width while default provoking semantics use LAST");
    raster[0].lineWidth = 1;
    VkPipelineRasterizationLineStateCreateInfoKHR explicit_line{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_LINE_STATE_CREATE_INFO_KHR};
    explicit_line.lineRasterizationMode = VK_LINE_RASTERIZATION_MODE_RECTANGULAR_KHR; explicit_line.pNext = &tail;
    raster[0].pNext = &explicit_line;
    require(create(device0, VK_NULL_HANDLE, 1, info, nullptr, outputs) == VK_SUCCESS && !selected_lines[0] && selected_last[0] &&
            selected_last_tail[0] == &explicit_line && explicit_line.pNext == &tail &&
            explicit_line.lineRasterizationMode == VK_LINE_RASTERIZATION_MODE_RECTANGULAR_KHR,
            "explicit rectangular line state survives independent LAST insertion");
    raster[0].pNext = &tail;
    retire_device(device0);
    // Reuse a caller-provided LAST feature alongside injected Bresenham.
    caller.provokingVertexLast = VK_TRUE;
    require(make_device(instance0, 0, device0, &caller, {VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME}) == VK_SUCCESS &&
            line_mock[0].feature_structs == 1 && line_mock[0].last_feature_structs == 1 && caller.provokingVertexLast == VK_TRUE &&
            line_mock[0].next_after_line == &caller && line_mock[0].enabled_extensions.size() == 2,
            "combined admission never duplicates a caller-provided LAST feature or extension");
    retire_device(device0);
    caller.provokingVertexLast = VK_FALSE;
    const auto disabled_last_creations = vispy_layer_vk_last_vertex_device_creations();
    require(make_device(instance0, 0, device0, &caller, {VK_EXT_PROVOKING_VERTEX_EXTENSION_NAME}) == VK_SUCCESS &&
            line_mock[0].enabled && !line_mock[0].last_enabled && line_mock[0].last_feature_structs == 1 &&
            caller.provokingVertexLast == VK_FALSE && vispy_layer_vk_last_vertex_device_creations() == disabled_last_creations &&
            vispy_layer_vk_bresenham_device_count() == 1,
            "caller-disabled LAST stays disabled while independently queried Bresenham is active");
    retire_device(device0);
    VkPhysicalDeviceLineRasterizationFeaturesKHR disabled_line{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_KHR};
    require(make_device(instance0, 0, device0, &disabled_line) == VK_SUCCESS && !line_mock[0].enabled &&
            line_mock[0].last_enabled && !vispy_layer_vk_bresenham_device_count() && disabled_line.bresenhamLines == VK_FALSE,
            "caller-disabled Bresenham remains disabled while independently admitted LAST stays active");
    retire_device(device0); retire_instance(instance0);
    vispy_layer_vk_enable_last_vertex(0); vispy_layer_vk_enable_bresenham(0);
    require(!vispy_layer_vk_active_instance_count() && !vispy_layer_vk_active_device_count(), "LAST dispatch retires with owning instances/devices");
}
}  // namespace

int main() {
    try {
        VkNegotiateLayerInterface negotiated{};
        negotiated.sType = LAYER_NEGOTIATE_INTERFACE_STRUCT;
        negotiated.loaderLayerInterfaceVersion = 5;
        require(vkNegotiateLoaderLayerInterfaceVersion(&negotiated) == VK_SUCCESS && negotiated.loaderLayerInterfaceVersion == 2,
                "portable loader interface negotiation");
        require(negotiated.pfnGetInstanceProcAddr && negotiated.pfnGetDeviceProcAddr && negotiated.pfnGetPhysicalDeviceProcAddr,
                "negotiation callback table");
        auto create_instance = reinterpret_cast<PFN_vkCreateInstance>(vispy_GetInstanceProcAddr(VK_NULL_HANDLE, "vkCreateInstance"));
        VkInstance instance[2]{};
        VkDevice device[2]{};
        VkQueue queue[2]{};
        for (int index = 0; index < 2; ++index) {
            VkLayerInstanceLink next{nullptr, index ? instance_proc1 : instance_proc0, nullptr};
            VkLayerInstanceCreateInfo link{};
            link.sType = VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO;
            link.function = VK_LAYER_LINK_INFO;
            link.u.pLayerInfo = &next;
            VkInstanceCreateInfo info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO}; info.pNext = &link;
            require(create_instance(&info, nullptr, &instance[index]) == VK_SUCCESS && !link.u.pLayerInfo, "instance link advancement");
            VkLayerDeviceLink device_next{nullptr, index ? instance_proc1 : instance_proc0, index ? device_proc1 : device_proc0};
            VkLayerDeviceCreateInfo device_link{};
            device_link.sType = VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO;
            device_link.function = VK_LAYER_LINK_INFO;
            device_link.u.pLayerInfo = &device_next;
            VkDeviceCreateInfo device_info{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO}; device_info.pNext = &device_link;
            auto create_device = reinterpret_cast<PFN_vkCreateDevice>(vispy_GetInstanceProcAddr(instance[index], "vkCreateDevice"));
            require(create_device(reinterpret_cast<VkPhysicalDevice>(&physical_handles[index]), &device_info, nullptr, &device[index]) == VK_SUCCESS,
                    "physical-device instance ownership");
            auto get = reinterpret_cast<PFN_vkGetDeviceQueue>(vispy_GetDeviceProcAddr(device[index], "vkGetDeviceQueue"));
            get(device[index], 0, 0, &queue[index]);
        }
        require(vispy_layer_vk_active_instance_count() == 2 && vispy_layer_vk_active_device_count() == 2, "simultaneous independent dispatch records");
        auto submit = reinterpret_cast<PFN_vkQueueSubmit>(vispy_GetInstanceProcAddr(instance[0], "vkQueueSubmit"));
        require(submit(queue[0], 3, nullptr, VK_NULL_HANDLE) == VK_SUCCESS, "first device downstream submit");
        require(submit(queue[1], 1, nullptr, VK_NULL_HANDLE) == VK_ERROR_DEVICE_LOST, "second device result preserved");
        require(native_calls[0] == 1 && native_calls[1] == 1 && vispy_layer_vk_submit_count() == 2, "count API calls rather than submit array entries");
        require(!vispy_GetDeviceProcAddr(device[0], "vkQueueSubmit2") && !vispy_GetDeviceProcAddr(device[1], "vkQueueSubmit2KHR"),
                "per-device core/KHR availability");
        auto khr = reinterpret_cast<PFN_vkQueueSubmit2KHR>(vispy_GetDeviceProcAddr(device[0], "vkQueueSubmit2KHR"));
        auto core = reinterpret_cast<PFN_vkQueueSubmit2>(vispy_GetDeviceProcAddr(device[1], "vkQueueSubmit2"));
        require(khr(queue[0], 0, nullptr, VK_NULL_HANDLE) == VK_SUCCESS && core(queue[1], 0, nullptr, VK_NULL_HANDLE) == VK_SUCCESS,
                "core and KHR downstream pointers stay distinct");
        require(vispy_GetDeviceProcAddr(device[0], "device_special") == reinterpret_cast<PFN_vkVoidFunction>(submit0) &&
                vispy_GetDeviceProcAddr(device[1], "device_special") == reinterpret_cast<PFN_vkVoidFunction>(submit1), "unintercepted per-device forwarding");
        std::thread first([&] { for (int i = 0; i < 1000; ++i) submit(queue[0], 0, nullptr, VK_NULL_HANDLE); });
        std::thread second([&] { for (int i = 0; i < 1000; ++i) submit(queue[1], 0, nullptr, VK_NULL_HANDLE); });
        first.join(); second.join();
        require(vispy_layer_vk_submit_count() == 2004 && native_calls[0] == 1002 && native_calls[1] == 1002, "concurrent queue dispatch/counter integrity");
        for (int index = 0; index < 2; ++index) {
            reinterpret_cast<PFN_vkDestroyDevice>(vispy_GetDeviceProcAddr(device[index], "vkDestroyDevice"))(device[index], nullptr);
            require(submit(queue[index], 0, nullptr, VK_NULL_HANDLE) == VK_ERROR_DEVICE_LOST, "retired queue dispatch removed");
            reinterpret_cast<PFN_vkDestroyInstance>(vispy_GetInstanceProcAddr(instance[index], "vkDestroyInstance"))(instance[index], nullptr);
        }
        require(!vispy_layer_vk_active_instance_count() && !vispy_layer_vk_active_device_count() && vispy_layer_vk_submit_count() == 2004,
                "all dispatch state retires without fabricated submits");
        require(destroyed_devices[0] == 1 && destroyed_devices[1] == 1 && destroyed_instances[0] == 1 && destroyed_instances[1] == 1,
                "native destroys forwarded once");
        line_contracts();
        last_vertex_contracts();
        memory_window_hook_contracts();
        memory_contracts();
        std::cout << "Vulkan dispatch, aliases, concurrency, retirement, Bresenham/LAST and actual device-memory CPU contracts passed\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
