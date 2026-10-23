// SPDX-License-Identifier: AGPL-3.0-only
// Offscreen diagnostic only. No VisPy/Dawn renderer path is changed or qualified.
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#define VK_NO_PROTOTYPES
#include <windows.h>
#include <vulkan/vulkan.h>
#include <spirv-tools/libspirv.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
static void check(VkResult result, const char* message) { if (result != VK_SUCCESS) throw std::runtime_error(std::string(message)+": "+std::to_string(result)); }
static std::string quoted(const std::string& text) {
    std::string result="\"";
    for (unsigned char c:text) {
        if (c=='\\' || c=='\"') { result+='\\'; result+=char(c); }
        else if (c<32) { const char* digits="0123456789abcdef"; result+="\\u00"; result+=digits[c>>4]; result+=digits[c&15]; }
        else result+=char(c);
    }
    return result+'\"';
}
static const char* vertex_source=R"(
OpCapability Shader
OpMemoryModel Logical GLSL450
OpEntryPoint Vertex %main "main" %input %position
OpDecorate %input Location 0
OpDecorate %position BuiltIn Position
%void = OpTypeVoid
%function = OpTypeFunction %void
%float = OpTypeFloat 32
%vec2 = OpTypeVector %float 2
%vec4 = OpTypeVector %float 4
%pin = OpTypePointer Input %vec2
%pout = OpTypePointer Output %vec4
%input = OpVariable %pin Input
%position = OpVariable %pout Output
%half = OpConstant %float 0.5
%one = OpConstant %float 1
%main = OpFunction %void None %function
%entry = OpLabel
%xy = OpLoad %vec2 %input
%x = OpCompositeExtract %float %xy 0
%y = OpCompositeExtract %float %xy 1
%out = OpCompositeConstruct %vec4 %x %y %half %one
OpStore %position %out
OpReturn
OpFunctionEnd
)";
static const char* fragment_source=R"(
OpCapability Shader
OpMemoryModel Logical GLSL450
OpEntryPoint Fragment %main "main" %color
OpExecutionMode %main OriginUpperLeft
OpDecorate %color Location 0
%void = OpTypeVoid
%function = OpTypeFunction %void
%float = OpTypeFloat 32
%vec4 = OpTypeVector %float 4
%pout = OpTypePointer Output %vec4
%color = OpVariable %pout Output
%one = OpConstant %float 1
%white = OpConstantComposite %vec4 %one %one %one %one
%main = OpFunction %void None %function
%entry = OpLabel
OpStore %color %white
OpReturn
OpFunctionEnd
)";
static std::vector<uint32_t> compile_shader(const char* text) {
    spvtools::SpirvTools tools(SPV_ENV_VULKAN_1_1);
    tools.SetMessageConsumer([](spv_message_level_t,const char*,const spv_position_t& p,const char* message) {
        std::cerr<<"SPIR-V "<<p.line<<":"<<p.column<<" "<<message<<"\n";
    });
    std::vector<uint32_t> words;
    require(tools.Assemble(text,&words),"SPIR-V assembly failed");
    require(tools.Validate(words),"SPIR-V validation failed");
    return words;
}
static void save_words(const std::filesystem::path& path,const std::vector<uint32_t>& words) {
    require(!std::filesystem::exists(path),"Preserve existing shader artifact");
    std::ofstream stream(path,std::ios::binary); stream.write(reinterpret_cast<const char*>(words.data()),words.size()*4);
    require(bool(stream),"Shader artifact write failed");
}
static std::vector<uint32_t> load_words(const char* path) {
    std::ifstream stream(path,std::ios::binary|std::ios::ate);
    require(bool(stream),"Shader artifact absent"); const auto size=stream.tellg();
    require(size>0 && size%4==0,"Invalid shader byte length");
    std::vector<uint32_t> words(size_t(size)/4); stream.seekg(0); stream.read(reinterpret_cast<char*>(words.data()),size);
    require(bool(stream),"Shader artifact read failed");
    spvtools::SpirvTools tools(SPV_ENV_VULKAN_1_1); require(tools.Validate(words),"Shader validation failed");
    return words;
}

#define INSTANCE_FUNCTIONS(X) X(vkDestroyInstance) X(vkEnumeratePhysicalDevices) X(vkGetPhysicalDeviceProperties) \
 X(vkGetPhysicalDeviceFeatures2) X(vkGetPhysicalDeviceQueueFamilyProperties) X(vkGetPhysicalDeviceMemoryProperties) \
 X(vkEnumerateDeviceExtensionProperties) X(vkGetPhysicalDeviceFormatProperties) X(vkCreateDevice) X(vkGetDeviceProcAddr)
#define DEVICE_FUNCTIONS(X) X(vkDestroyDevice) X(vkDeviceWaitIdle) X(vkGetDeviceQueue) X(vkCreateBuffer) X(vkDestroyBuffer) \
 X(vkGetBufferMemoryRequirements) X(vkAllocateMemory) X(vkFreeMemory) X(vkBindBufferMemory) X(vkMapMemory) X(vkUnmapMemory) \
 X(vkCreateImage) X(vkDestroyImage) X(vkGetImageMemoryRequirements) X(vkBindImageMemory) X(vkCreateImageView) X(vkDestroyImageView) \
 X(vkCreateRenderPass) X(vkDestroyRenderPass) X(vkCreateFramebuffer) X(vkDestroyFramebuffer) X(vkCreateShaderModule) X(vkDestroyShaderModule) \
 X(vkCreatePipelineLayout) X(vkDestroyPipelineLayout) X(vkCreateGraphicsPipelines) X(vkDestroyPipeline) \
 X(vkCreateCommandPool) X(vkDestroyCommandPool) X(vkAllocateCommandBuffers) X(vkResetCommandBuffer) X(vkBeginCommandBuffer) \
 X(vkEndCommandBuffer) X(vkCmdPipelineBarrier) X(vkCmdBeginRenderPass) X(vkCmdEndRenderPass) X(vkCmdBindPipeline) \
 X(vkCmdBindVertexBuffers) X(vkCmdSetLineWidth) X(vkCmdDraw) X(vkCmdCopyImageToBuffer) X(vkCreateFence) X(vkDestroyFence) \
 X(vkResetFences) X(vkQueueSubmit) X(vkWaitForFences)

struct Renderer {
    HMODULE library=nullptr;
    PFN_vkGetInstanceProcAddr get_instance=nullptr;
#define DECLARE(name) PFN_##name name=nullptr;
    INSTANCE_FUNCTIONS(DECLARE) DEVICE_FUNCTIONS(DECLARE)
#undef DECLARE
    VkInstance instance=VK_NULL_HANDLE; VkPhysicalDevice physical=VK_NULL_HANDLE;
    VkDevice device=VK_NULL_HANDLE; VkQueue queue=VK_NULL_HANDLE; uint32_t queue_family=0;
    VkPhysicalDeviceProperties properties{}; VkPhysicalDeviceMemoryProperties memory{};
    VkBuffer vertex=VK_NULL_HANDLE,readback=VK_NULL_HANDLE;
    VkDeviceMemory vertex_memory=VK_NULL_HANDLE,read_memory=VK_NULL_HANDLE,image_memory=VK_NULL_HANDLE;
    void* vertex_map=nullptr; void* read_map=nullptr;
    VkImage image=VK_NULL_HANDLE; VkImageView view=VK_NULL_HANDLE;
    VkRenderPass render_pass=VK_NULL_HANDLE; VkFramebuffer framebuffer=VK_NULL_HANDLE;
    VkShaderModule vertex_shader=VK_NULL_HANDLE,fragment_shader=VK_NULL_HANDLE;
    VkPipelineLayout layout=VK_NULL_HANDLE; VkPipeline pipeline=VK_NULL_HANDLE;
    VkCommandPool pool=VK_NULL_HANDLE; VkCommandBuffer commands=VK_NULL_HANDLE; VkFence fence=VK_NULL_HANDLE;
    std::string extension;
    uint32_t memory_type(uint32_t bits,VkMemoryPropertyFlags flags) {
        for (uint32_t i=0;i<memory.memoryTypeCount;++i) if ((bits&(1u<<i)) && (memory.memoryTypes[i].propertyFlags&flags)==flags) return i;
        throw std::runtime_error("Required memory type unavailable");
    }
    void buffer(VkDeviceSize size,VkBufferUsageFlags usage,VkBuffer& handle,VkDeviceMemory& allocation,void*& mapped) {
        VkBufferCreateInfo info{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO}; info.size=size; info.usage=usage;
        check(vkCreateBuffer(device,&info,nullptr,&handle),"CreateBuffer");
        VkMemoryRequirements requirements{}; vkGetBufferMemoryRequirements(device,handle,&requirements);
        VkMemoryAllocateInfo alloc{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO}; alloc.allocationSize=requirements.size;
        alloc.memoryTypeIndex=memory_type(requirements.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkAllocateMemory(device,&alloc,nullptr,&allocation),"AllocateBufferMemory");
        check(vkBindBufferMemory(device,handle,allocation,0),"BindBufferMemory");
        check(vkMapMemory(device,allocation,0,size,0,&mapped),"MapBufferMemory");
    }
    VkShaderModule shader(const std::vector<uint32_t>& words) {
        VkShaderModuleCreateInfo info{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO}; info.codeSize=words.size()*4; info.pCode=words.data();
        VkShaderModule handle=VK_NULL_HANDLE; check(vkCreateShaderModule(device,&info,nullptr,&handle),"CreateShaderModule"); return handle;
    }
    void initialize(const std::vector<uint32_t>& vs,const std::vector<uint32_t>& fs) {
        library=LoadLibraryW(L"vulkan-1.dll"); require(library!=nullptr,"Vulkan loader absent");
        get_instance=reinterpret_cast<PFN_vkGetInstanceProcAddr>(GetProcAddress(library,"vkGetInstanceProcAddr")); require(get_instance!=nullptr,"GetInstanceProcAddr absent");
        auto create_instance=reinterpret_cast<PFN_vkCreateInstance>(get_instance(VK_NULL_HANDLE,"vkCreateInstance")); require(create_instance!=nullptr,"CreateInstance absent");
        VkApplicationInfo application{VK_STRUCTURE_TYPE_APPLICATION_INFO}; application.pApplicationName="VisPy native smooth diagnostic"; application.apiVersion=VK_API_VERSION_1_1;
        VkInstanceCreateInfo info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO}; info.pApplicationInfo=&application;
        check(create_instance(&info,nullptr,&instance),"CreateInstance");
#define LOAD_INSTANCE(name) name=reinterpret_cast<PFN_##name>(get_instance(instance,#name)); require(name!=nullptr,#name " absent");
        INSTANCE_FUNCTIONS(LOAD_INSTANCE)
#undef LOAD_INSTANCE
        uint32_t count=0; check(vkEnumeratePhysicalDevices(instance,&count,nullptr),"EnumerateDevices");
        std::vector<VkPhysicalDevice> devices(count); check(vkEnumeratePhysicalDevices(instance,&count,devices.data()),"EnumerateDevices");
        for (auto candidate:devices) { VkPhysicalDeviceProperties p{}; vkGetPhysicalDeviceProperties(candidate,&p);
            if (p.vendorID==0x10de && p.deviceType==VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU) {
                require(physical==VK_NULL_HANDLE,"Multiple NVIDIA devices require an explicit selector"); physical=candidate; properties=p;
            }
        }
        require(physical!=VK_NULL_HANDLE && std::string(properties.deviceName)=="NVIDIA GeForce RTX 4090","Expected NVIDIA RTX4090 absent");
        VkPhysicalDeviceLineRasterizationFeaturesKHR lines{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_KHR};
        VkPhysicalDeviceFeatures2 features{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2}; features.pNext=&lines;
        vkGetPhysicalDeviceFeatures2(physical,&features);
        require(features.features.wideLines && lines.smoothLines && lines.rectangularLines,"Native smooth/wide/rectangular features absent");
        count=0; check(vkEnumerateDeviceExtensionProperties(physical,nullptr,&count,nullptr),"EnumerateExtensions");
        std::vector<VkExtensionProperties> extensions(count); check(vkEnumerateDeviceExtensionProperties(physical,nullptr,&count,extensions.data()),"EnumerateExtensions");
        for (const auto& e:extensions) if (std::string(e.extensionName)==VK_KHR_LINE_RASTERIZATION_EXTENSION_NAME) extension=e.extensionName;
        if (extension.empty()) for (const auto& e:extensions) if (std::string(e.extensionName)==VK_EXT_LINE_RASTERIZATION_EXTENSION_NAME) extension=e.extensionName;
        require(!extension.empty(),"Line rasterization extension absent");
        count=0; vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,nullptr);
        std::vector<VkQueueFamilyProperties> queues(count); vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,queues.data());
        auto q=std::find_if(queues.begin(),queues.end(),[](const auto& value){return value.queueCount && (value.queueFlags&VK_QUEUE_GRAPHICS_BIT);});
        require(q!=queues.end(),"Graphics queue absent"); queue_family=uint32_t(q-queues.begin());
        float priority=1; VkDeviceQueueCreateInfo queue_info{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO}; queue_info.queueFamilyIndex=queue_family; queue_info.queueCount=1; queue_info.pQueuePriorities=&priority;
        VkPhysicalDeviceFeatures enabled{}; enabled.wideLines=VK_TRUE;
        VkPhysicalDeviceLineRasterizationFeaturesKHR enabled_lines{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_LINE_RASTERIZATION_FEATURES_KHR}; enabled_lines.rectangularLines=enabled_lines.smoothLines=VK_TRUE;
        const char* extension_name=extension.c_str(); VkDeviceCreateInfo device_info{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
        device_info.pNext=&enabled_lines; device_info.queueCreateInfoCount=1; device_info.pQueueCreateInfos=&queue_info; device_info.pEnabledFeatures=&enabled;
        device_info.enabledExtensionCount=1; device_info.ppEnabledExtensionNames=&extension_name;
        check(vkCreateDevice(physical,&device_info,nullptr,&device),"CreateDevice");
#define LOAD_DEVICE(name) name=reinterpret_cast<PFN_##name>(vkGetDeviceProcAddr(device,#name)); require(name!=nullptr,#name " absent");
        DEVICE_FUNCTIONS(LOAD_DEVICE)
#undef LOAD_DEVICE
        vkGetDeviceQueue(device,queue_family,0,&queue); vkGetPhysicalDeviceMemoryProperties(physical,&memory);
        VkFormatProperties format{}; vkGetPhysicalDeviceFormatProperties(physical,VK_FORMAT_R8G8B8A8_UNORM,&format);
        require((format.optimalTilingFeatures&(VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT|VK_FORMAT_FEATURE_TRANSFER_SRC_BIT))==(VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT|VK_FORMAT_FEATURE_TRANSFER_SRC_BIT),"RGBA8 attachment/copy unsupported");
        buffer(16,VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,vertex,vertex_memory,vertex_map);
        buffer(64*64*4,VK_BUFFER_USAGE_TRANSFER_DST_BIT,readback,read_memory,read_map);
        VkImageCreateInfo image_info{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO}; image_info.imageType=VK_IMAGE_TYPE_2D; image_info.format=VK_FORMAT_R8G8B8A8_UNORM;
        image_info.extent={64,64,1}; image_info.mipLevels=image_info.arrayLayers=1; image_info.samples=VK_SAMPLE_COUNT_1_BIT;
        image_info.tiling=VK_IMAGE_TILING_OPTIMAL; image_info.usage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
        check(vkCreateImage(device,&image_info,nullptr,&image),"CreateImage");
        VkMemoryRequirements image_requirements{}; vkGetImageMemoryRequirements(device,image,&image_requirements);
        VkMemoryAllocateInfo allocation{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO}; allocation.allocationSize=image_requirements.size; allocation.memoryTypeIndex=memory_type(image_requirements.memoryTypeBits,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkAllocateMemory(device,&allocation,nullptr,&image_memory),"AllocateImageMemory"); check(vkBindImageMemory(device,image,image_memory,0),"BindImageMemory");
        VkImageViewCreateInfo view_info{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO}; view_info.image=image; view_info.viewType=VK_IMAGE_VIEW_TYPE_2D; view_info.format=VK_FORMAT_R8G8B8A8_UNORM;
        view_info.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}; check(vkCreateImageView(device,&view_info,nullptr,&view),"CreateImageView");
        VkAttachmentDescription attachment{}; attachment.format=VK_FORMAT_R8G8B8A8_UNORM; attachment.samples=VK_SAMPLE_COUNT_1_BIT;
        attachment.loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR; attachment.storeOp=VK_ATTACHMENT_STORE_OP_STORE; attachment.stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE; attachment.stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachment.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED; attachment.finalLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        VkAttachmentReference color{0,VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL}; VkSubpassDescription subpass{}; subpass.pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS; subpass.colorAttachmentCount=1; subpass.pColorAttachments=&color;
        VkSubpassDependency dependencies[2]{};
        dependencies[0]={VK_SUBPASS_EXTERNAL,0,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,0,VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,0};
        dependencies[1]={0,VK_SUBPASS_EXTERNAL,VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,VK_ACCESS_TRANSFER_READ_BIT,0};
        VkRenderPassCreateInfo pass{VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO}; pass.attachmentCount=1; pass.pAttachments=&attachment; pass.subpassCount=1; pass.pSubpasses=&subpass; pass.dependencyCount=2; pass.pDependencies=dependencies;
        check(vkCreateRenderPass(device,&pass,nullptr,&render_pass),"CreateRenderPass");
        VkFramebufferCreateInfo fb{VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO}; fb.renderPass=render_pass; fb.attachmentCount=1; fb.pAttachments=&view; fb.width=fb.height=64; fb.layers=1;
        check(vkCreateFramebuffer(device,&fb,nullptr,&framebuffer),"CreateFramebuffer");
        vertex_shader=shader(vs); fragment_shader=shader(fs);
        VkPipelineShaderStageCreateInfo stages[2]{}; stages[0]={VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,nullptr,0,VK_SHADER_STAGE_VERTEX_BIT,vertex_shader,"main",nullptr};
        stages[1]={VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,nullptr,0,VK_SHADER_STAGE_FRAGMENT_BIT,fragment_shader,"main",nullptr};
        VkVertexInputBindingDescription binding{0,8,VK_VERTEX_INPUT_RATE_VERTEX}; VkVertexInputAttributeDescription attribute{0,0,VK_FORMAT_R32G32_SFLOAT,0};
        VkPipelineVertexInputStateCreateInfo input{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO}; input.vertexBindingDescriptionCount=input.vertexAttributeDescriptionCount=1; input.pVertexBindingDescriptions=&binding; input.pVertexAttributeDescriptions=&attribute;
        VkPipelineInputAssemblyStateCreateInfo assembly{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO}; assembly.topology=VK_PRIMITIVE_TOPOLOGY_LINE_LIST;
        VkViewport viewport{0,0,64,64,0,1}; VkRect2D scissor{{0,0},{64,64}};
        VkPipelineViewportStateCreateInfo viewport_state{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO}; viewport_state.viewportCount=viewport_state.scissorCount=1; viewport_state.pViewports=&viewport; viewport_state.pScissors=&scissor;
        VkPipelineRasterizationLineStateCreateInfoKHR line_state{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_LINE_STATE_CREATE_INFO_KHR}; line_state.lineRasterizationMode=VK_LINE_RASTERIZATION_MODE_RECTANGULAR_SMOOTH_KHR;
        VkPipelineRasterizationStateCreateInfo raster{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO}; raster.pNext=&line_state; raster.polygonMode=VK_POLYGON_MODE_FILL; raster.cullMode=VK_CULL_MODE_NONE; raster.frontFace=VK_FRONT_FACE_COUNTER_CLOCKWISE; raster.lineWidth=1;
        VkPipelineMultisampleStateCreateInfo multisample{VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO}; multisample.rasterizationSamples=VK_SAMPLE_COUNT_1_BIT;
        VkPipelineColorBlendAttachmentState blend{}; blend.colorWriteMask=15; VkPipelineColorBlendStateCreateInfo color_blend{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO}; color_blend.attachmentCount=1; color_blend.pAttachments=&blend;
        VkDynamicState dynamic_state=VK_DYNAMIC_STATE_LINE_WIDTH; VkPipelineDynamicStateCreateInfo dynamic{VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO}; dynamic.dynamicStateCount=1; dynamic.pDynamicStates=&dynamic_state;
        VkPipelineLayoutCreateInfo layout_info{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO}; check(vkCreatePipelineLayout(device,&layout_info,nullptr,&layout),"CreatePipelineLayout");
        VkGraphicsPipelineCreateInfo pipeline_info{VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO}; pipeline_info.stageCount=2; pipeline_info.pStages=stages;
        pipeline_info.pVertexInputState=&input; pipeline_info.pInputAssemblyState=&assembly; pipeline_info.pViewportState=&viewport_state;
        pipeline_info.pRasterizationState=&raster; pipeline_info.pMultisampleState=&multisample; pipeline_info.pColorBlendState=&color_blend; pipeline_info.pDynamicState=&dynamic;
        pipeline_info.layout=layout; pipeline_info.renderPass=render_pass;
        check(vkCreateGraphicsPipelines(device,VK_NULL_HANDLE,1,&pipeline_info,nullptr,&pipeline),"CreateGraphicsPipeline");
        VkCommandPoolCreateInfo pool_info{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO}; pool_info.queueFamilyIndex=queue_family; pool_info.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        check(vkCreateCommandPool(device,&pool_info,nullptr,&pool),"CreateCommandPool"); VkCommandBufferAllocateInfo cmd{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO}; cmd.commandPool=pool; cmd.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY; cmd.commandBufferCount=1;
        check(vkAllocateCommandBuffers(device,&cmd,&commands),"AllocateCommandBuffer"); VkFenceCreateInfo fence_info{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO}; check(vkCreateFence(device,&fence_info,nullptr,&fence),"CreateFence");
    }
    void draw(const std::array<float,5>& row,std::ofstream& output) {
        require(row[4]>=properties.limits.lineWidthRange[0] && row[4]<=properties.limits.lineWidthRange[1],"Line width outside device range");
        const float granularity=properties.limits.lineWidthGranularity;
        require(granularity==0 || std::abs((row[4]-properties.limits.lineWidthRange[0])/granularity-std::round((row[4]-properties.limits.lineWidthRange[0])/granularity))<1e-5f,"Line width off device granularity");
        std::memcpy(vertex_map,row.data(),16);
        check(vkResetFences(device,1,&fence),"ResetFence"); check(vkResetCommandBuffer(commands,0),"ResetCommandBuffer");
        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO}; begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT; check(vkBeginCommandBuffer(commands,&begin),"BeginCommands");
        VkBufferMemoryBarrier host{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER}; host.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT; host.dstAccessMask=VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT; host.srcQueueFamilyIndex=host.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED; host.buffer=vertex; host.size=16;
        vkCmdPipelineBarrier(commands,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_VERTEX_INPUT_BIT,0,0,nullptr,1,&host,0,nullptr);
        VkClearValue clear{}; VkRenderPassBeginInfo pass{VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO}; pass.renderPass=render_pass; pass.framebuffer=framebuffer; pass.renderArea={{0,0},{64,64}}; pass.clearValueCount=1; pass.pClearValues=&clear;
        vkCmdBeginRenderPass(commands,&pass,VK_SUBPASS_CONTENTS_INLINE); vkCmdBindPipeline(commands,VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline);
        VkDeviceSize offset=0; vkCmdBindVertexBuffers(commands,0,1,&vertex,&offset); vkCmdSetLineWidth(commands,row[4]); vkCmdDraw(commands,2,1,0,0); vkCmdEndRenderPass(commands);
        VkBufferImageCopy copy{}; copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1}; copy.imageExtent={64,64,1};
        vkCmdCopyImageToBuffer(commands,image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,readback,1,&copy);
        VkBufferMemoryBarrier read{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER}; read.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT; read.dstAccessMask=VK_ACCESS_HOST_READ_BIT; read.srcQueueFamilyIndex=read.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED; read.buffer=readback; read.size=64*64*4;
        vkCmdPipelineBarrier(commands,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,nullptr,1,&read,0,nullptr);
        check(vkEndCommandBuffer(commands),"EndCommands"); VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO}; submit.commandBufferCount=1; submit.pCommandBuffers=&commands;
        check(vkQueueSubmit(queue,1,&submit,fence),"QueueSubmit"); check(vkWaitForFences(device,1,&fence,VK_TRUE,60000000000ull),"WaitForFrameFence");
        // Positive Vulkan viewport matches the numerical GL window coordinates;
        // normalize the copied image to the same top-left row order as gloo.read_pixels.
        for (int y=63;y>=0;--y) output.write(static_cast<const char*>(read_map)+y*64*4,64*4);
        require(bool(output),"Raw frame write failed");
    }
    void close() {
        const VkResult wait_result=(device && vkDeviceWaitIdle) ? vkDeviceWaitIdle(device) : VK_SUCCESS;
#define DROP(function,handle) if (handle) { function(device,handle,nullptr); handle=VK_NULL_HANDLE; }
        if (device) {
            DROP(vkDestroyFence,fence) DROP(vkDestroyCommandPool,pool) commands=VK_NULL_HANDLE;
            DROP(vkDestroyPipeline,pipeline) DROP(vkDestroyPipelineLayout,layout)
            DROP(vkDestroyShaderModule,vertex_shader) DROP(vkDestroyShaderModule,fragment_shader)
            DROP(vkDestroyFramebuffer,framebuffer) DROP(vkDestroyRenderPass,render_pass)
            DROP(vkDestroyImageView,view) DROP(vkDestroyImage,image)
            if (vertex_map) { vkUnmapMemory(device,vertex_memory); vertex_map=nullptr; }
            if (read_map) { vkUnmapMemory(device,read_memory); read_map=nullptr; }
            DROP(vkDestroyBuffer,vertex) DROP(vkDestroyBuffer,readback)
            DROP(vkFreeMemory,vertex_memory) DROP(vkFreeMemory,read_memory) DROP(vkFreeMemory,image_memory)
            vkDestroyDevice(device,nullptr); device=VK_NULL_HANDLE;
            queue=VK_NULL_HANDLE;
        }
#undef DROP
        if (instance && vkDestroyInstance) { vkDestroyInstance(instance,nullptr); instance=VK_NULL_HANDLE; }
        physical=VK_NULL_HANDLE;
        if (library) { FreeLibrary(library); library=nullptr; }
        check(wait_result,"DeviceWaitIdle at close");
    }
    bool closed() const {
        return !library && !instance && !device && !queue && !vertex && !readback && !image && !view &&
            !vertex_memory && !read_memory && !image_memory && !vertex_map && !read_map && !render_pass &&
            !framebuffer && !vertex_shader && !fragment_shader && !layout && !pipeline && !pool && !commands && !fence;
    }
    ~Renderer() { try { close(); } catch (...) {} }
};

int main(int argc,char** argv) {
    uint32_t written=0; bool graphics_attempted=false;
    try {
        if (argc==3 && std::string(argv[1])=="--compile-shaders") {
            const std::filesystem::path folder=argv[2];
            save_words(folder/"vertex.spv",compile_shader(vertex_source)); save_words(folder/"fragment.spv",compile_shader(fragment_source));
            std::cout<<"{\"status\":\"PASS_CPU_SHADER_VALIDATION_ONLY\",\"graphics_attempted\":false}\n"; return 0;
        }
        require(argc==6,"Usage: input.bin vertex.spv fragment.spv output.rgba result.json");
        require(!std::filesystem::exists(argv[4]) && !std::filesystem::exists(argv[5]),"Preserve every earlier attempt");
        std::ifstream input(argv[1],std::ios::binary); uint32_t count=0; input.read(reinterpret_cast<char*>(&count),4);
        require(bool(input) && count>0 && count<=20000,"Invalid input row count");
        static_assert(sizeof(float)==4 && sizeof(std::array<float,5>)==20);
        std::vector<std::array<float,5>> rows(count); input.read(reinterpret_cast<char*>(rows.data()),count*20);
        require(bool(input) && input.peek()==std::char_traits<char>::eof(),"Input size differs from descriptor count");
        for (const auto& row:rows) { for (float value:row) require(std::isfinite(value),"Nonfinite input");
            require(row[4]>=1 && row[4]<=8,"Input width outside diagnostic domain");
            for (int i=0;i<4;++i) require(row[i]>-1 && row[i]<1,"Input endpoint outside diagnostic domain");
        }
        const auto vs=load_words(argv[2]),fs=load_words(argv[3]);
        std::ofstream raw(argv[4],std::ios::binary); require(bool(raw),"Raw output open failed");
        Renderer renderer; graphics_attempted=true; renderer.initialize(vs,fs);
        const auto properties=renderer.properties; const auto extension=renderer.extension;
        for (const auto& row:rows) { renderer.draw(row,raw); ++written;
            if (written%256==0) std::cout<<"{\"stage\":\"native-smooth\",\"frames\":"<<written<<"}\n"<<std::flush;
        }
        raw.close(); require(bool(raw),"Raw output close failed"); renderer.close();
        require(renderer.closed(),"Native resources remain open");
        require(std::filesystem::file_size(argv[4])==uint64_t(count)*64*64*4,"Raw output size differs from count");
        char module[32768]{}; const DWORD module_size=GetModuleFileNameA(nullptr,module,sizeof(module));
        require(module_size>0 && module_size<sizeof(module),"Module identity absent or truncated");
        std::ofstream report(argv[5]);
        report<<"{\"status\":\"PASS_NATIVE_SMOOTH_DIAGNOSTIC_PENDING_REVIEW\",\"process_exit\":0,\"pid\":"<<GetCurrentProcessId()
            <<",\"module\":"<<quoted(module)<<",\"frames\":"<<written<<",\"device\":"<<quoted(properties.deviceName)
            <<",\"vendor_id\":"<<properties.vendorID<<",\"device_id\":"<<properties.deviceID<<",\"driver_version\":"<<properties.driverVersion
            <<",\"api_version\":"<<properties.apiVersion<<",\"smooth_lines_enabled\":true,\"wide_lines_enabled\":true"
            <<",\"pipeline_creations\":1,\"draw_commands\":"<<written<<",\"copy_commands\":"<<written
            <<",\"extension\":"<<quoted(extension)<<",\"viewport\":\"positive-height; copied rows reversed\",\"depth_coordinate\":0.5"
            <<",\"resources_closed\":true,\"model_selected\":false,\"renderer_qualified\":false,\"original13complete\":false}\n";
        report.close(); require(bool(report),"Result write failed"); std::cout<<"{\"status\":\"PASS_NATIVE_SMOOTH_DIAGNOSTIC_PENDING_REVIEW\",\"frames\":"<<written<<"}\n"; return 0;
    } catch (const std::exception& error) {
        std::cerr<<"native smooth diagnostic: "<<error.what()<<"\n";
        if (argc==6 && !std::filesystem::exists(argv[5])) {
            std::ofstream report(argv[5]); report<<"{\"status\":\"FAILED_NATIVE_SMOOTH_DIAGNOSTIC\",\"process_exit\":1,\"frames\":"<<written
                <<",\"graphics_attempted\":"<<(graphics_attempted?"true":"false")<<",\"error\":"<<quoted(error.what())<<",\"model_selected\":false,\"renderer_qualified\":false}\n";
        }
        return 1;
    }
}
