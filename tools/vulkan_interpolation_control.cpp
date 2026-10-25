// SPDX-License-Identifier: AGPL-3.0-only
// Independent Vulkan scalar interpolation control: no VisPy, Dawn or translator.
#include <vulkan/vulkan.h>
#include <spirv/unified1/spirv.hpp11>
#include <algorithm>
#include <vector>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <stdexcept>

void check(VkResult result) {
    if (result != VK_SUCCESS) throw std::runtime_error("Vulkan result " + std::to_string(result));
}
struct Spirv {
    std::vector<uint32_t> words{0x07230203,0x00010000,0,64,0};
    void op(spv::Op code, std::initializer_list<uint32_t> args) {
        words.push_back((uint32_t(args.size()+1)<<16)|uint32_t(code));
        words.insert(words.end(),args);
    }
};
Spirv shader(bool vertex, bool linear) {
    Spirv s;
    s.op(spv::Op::OpCapability,{uint32_t(spv::Capability::Shader)});
    s.op(spv::Op::OpMemoryModel,{0,1});
    if (vertex) s.op(spv::Op::OpEntryPoint,{0,20,0x6e69616d,0,10,11,12,13});
    else {s.op(spv::Op::OpEntryPoint,{4,20,0x6e69616d,0,11,12});s.op(spv::Op::OpExecutionMode,{20,7});}
    s.op(spv::Op::OpDecorate,{12,30,vertex?1u:0u});
    if (linear) s.op(spv::Op::OpDecorate,{vertex?13u:12u,13});
    if (vertex) {
        s.op(spv::Op::OpDecorate,{10,30,0});s.op(spv::Op::OpDecorate,{11,11,0});
        s.op(spv::Op::OpDecorate,{13,30,0});
    } else s.op(spv::Op::OpDecorate,{11,30,0});
    s.op(spv::Op::OpTypeVoid,{1});s.op(spv::Op::OpTypeFunction,{2,1});
    s.op(spv::Op::OpTypeFloat,{3,32});s.op(spv::Op::OpTypeVector,{5,3,4});
    s.op(spv::Op::OpTypePointer,{6,1,5});s.op(spv::Op::OpTypePointer,{7,3,5});
    s.op(spv::Op::OpTypePointer,{14,1,3});s.op(spv::Op::OpTypePointer,{15,3,3});
    s.op(spv::Op::OpConstant,{3,8,0});s.op(spv::Op::OpConstant,{3,9,0x3f800000});
    s.op(spv::Op::OpConstant,{3,16,0x40400000});
    s.op(spv::Op::OpVariable,{7,11,3});s.op(spv::Op::OpVariable,{14,12,1});
    if (vertex) {s.op(spv::Op::OpVariable,{6,10,1});s.op(spv::Op::OpVariable,{15,13,3});}
    s.op(spv::Op::OpFunction,{1,20,0,2});s.op(spv::Op::OpLabel,{21});
    if (vertex) {
        s.op(spv::Op::OpLoad,{5,22,10});s.op(spv::Op::OpStore,{11,22});
        s.op(spv::Op::OpLoad,{3,23,12});s.op(spv::Op::OpStore,{13,23});
    } else {
        s.op(spv::Op::OpLoad,{3,22,12});s.op(spv::Op::OpFDiv,{3,23,22,16});
        s.op(spv::Op::OpCompositeConstruct,{5,24,23,8,8,9});s.op(spv::Op::OpStore,{11,24});
    }
    s.op(spv::Op::OpReturn,{});s.op(spv::Op::OpFunctionEnd,{});return s;
}

int main() try {
    constexpr uint32_t W=16,H=16;
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.apiVersion=VK_API_VERSION_1_3;
    VkInstanceCreateInfo ic{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};ic.pApplicationInfo=&app;
    VkInstance instance;check(vkCreateInstance(&ic,nullptr,&instance));
    uint32_t count=0;check(vkEnumeratePhysicalDevices(instance,&count,nullptr));
    std::vector<VkPhysicalDevice> devices(count);check(vkEnumeratePhysicalDevices(instance,&count,devices.data()));
    if(!count)throw std::runtime_error("no Vulkan device");auto gpu=devices[0];
    VkPhysicalDeviceProperties properties;vkGetPhysicalDeviceProperties(gpu,&properties);
    std::printf("DEVICE %s api=%u driver=%u\n",properties.deviceName,properties.apiVersion,properties.driverVersion);
    vkGetPhysicalDeviceQueueFamilyProperties(gpu,&count,nullptr);std::vector<VkQueueFamilyProperties> families(count);
    vkGetPhysicalDeviceQueueFamilyProperties(gpu,&count,families.data());uint32_t family=0;
    while(family<count && !(families[family].queueFlags&VK_QUEUE_GRAPHICS_BIT))++family;
    if(family==count)throw std::runtime_error("no graphics queue");
    float priority=1;VkDeviceQueueCreateInfo qc{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
    qc.queueFamilyIndex=family;qc.queueCount=1;qc.pQueuePriorities=&priority;
    VkPhysicalDeviceDynamicRenderingFeatures dynamic{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DYNAMIC_RENDERING_FEATURES};dynamic.dynamicRendering=VK_TRUE;
    VkDeviceCreateInfo dc{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};dc.pNext=&dynamic;dc.queueCreateInfoCount=1;dc.pQueueCreateInfos=&qc;
    VkDevice device;check(vkCreateDevice(gpu,&dc,nullptr,&device));VkQueue queue;vkGetDeviceQueue(device,family,0,&queue);
    VkPhysicalDeviceMemoryProperties memory;vkGetPhysicalDeviceMemoryProperties(gpu,&memory);
    auto allocate=[&](VkMemoryRequirements req,VkMemoryPropertyFlags flags) {
        uint32_t n=0;for(;n<memory.memoryTypeCount;++n)if((req.memoryTypeBits&(1u<<n)) &&
            (memory.memoryTypes[n].propertyFlags&flags)==flags)break;
        if(n==memory.memoryTypeCount)throw std::runtime_error("no compatible memory type");
        VkMemoryAllocateInfo info{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};info.allocationSize=req.size;info.memoryTypeIndex=n;
        VkDeviceMemory result;check(vkAllocateMemory(device,&info,nullptr,&result));return result;
    };
    struct Buffer{VkBuffer handle;VkDeviceMemory memory;void* mapped;};
    auto make_buffer=[&](VkDeviceSize size,VkBufferUsageFlags usage) {
        Buffer result{};VkBufferCreateInfo ci{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};ci.size=size;ci.usage=usage;
        check(vkCreateBuffer(device,&ci,nullptr,&result.handle));VkMemoryRequirements req;vkGetBufferMemoryRequirements(device,result.handle,&req);
        result.memory=allocate(req,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkBindBufferMemory(device,result.handle,result.memory,0));check(vkMapMemory(device,result.memory,0,VK_WHOLE_SIZE,0,&result.mapped));return result;
    };
    Buffer vertices=make_buffer(3*5*sizeof(float),VK_BUFFER_USAGE_VERTEX_BUFFER_BIT),readback=make_buffer(W*H*4,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    VkImageCreateInfo image_ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};image_ci.imageType=VK_IMAGE_TYPE_2D;image_ci.format=VK_FORMAT_R8G8B8A8_UNORM;
    image_ci.extent={W,H,1};image_ci.mipLevels=image_ci.arrayLayers=1;image_ci.samples=VK_SAMPLE_COUNT_1_BIT;
    image_ci.tiling=VK_IMAGE_TILING_OPTIMAL;image_ci.usage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    VkImage image;check(vkCreateImage(device,&image_ci,nullptr,&image));VkMemoryRequirements req;vkGetImageMemoryRequirements(device,image,&req);
    auto image_memory=allocate(req,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);check(vkBindImageMemory(device,image,image_memory,0));
    VkImageViewCreateInfo view_ci{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};view_ci.image=image;view_ci.viewType=VK_IMAGE_VIEW_TYPE_2D;
    view_ci.format=image_ci.format;view_ci.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};VkImageView view;check(vkCreateImageView(device,&view_ci,nullptr,&view));
    VkPipelineLayoutCreateInfo layout_ci{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};VkPipelineLayout layout;check(vkCreatePipelineLayout(device,&layout_ci,nullptr,&layout));
    VkVertexInputBindingDescription binding{0,5*sizeof(float),VK_VERTEX_INPUT_RATE_VERTEX};
    VkVertexInputAttributeDescription attributes[]={{0,0,VK_FORMAT_R32G32B32A32_SFLOAT,0},{1,0,VK_FORMAT_R32_SFLOAT,4*sizeof(float)}};
    VkPipelineVertexInputStateCreateInfo vi{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};vi.vertexBindingDescriptionCount=1;vi.pVertexBindingDescriptions=&binding;vi.vertexAttributeDescriptionCount=2;vi.pVertexAttributeDescriptions=attributes;
    VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};ia.topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    VkViewport viewport{0,0,float(W),float(H),0,1};VkRect2D scissor{{0,0},{W,H}};
    VkPipelineViewportStateCreateInfo vp{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};vp.viewportCount=vp.scissorCount=1;vp.pViewports=&viewport;vp.pScissors=&scissor;
    VkPipelineRasterizationStateCreateInfo raster{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO};raster.polygonMode=VK_POLYGON_MODE_FILL;raster.cullMode=VK_CULL_MODE_NONE;raster.lineWidth=1;
    VkPipelineMultisampleStateCreateInfo ms{VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO};ms.rasterizationSamples=VK_SAMPLE_COUNT_1_BIT;
    VkPipelineColorBlendAttachmentState blend{};blend.colorWriteMask=15;
    VkPipelineColorBlendStateCreateInfo cb{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};cb.attachmentCount=1;cb.pAttachments=&blend;
    VkPipelineRenderingCreateInfo rendering{VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO};rendering.colorAttachmentCount=1;rendering.pColorAttachmentFormats=&image_ci.format;
    VkPipeline pipelines[2];VkShaderModule modules[4];
    for(int linear=0;linear<2;++linear) {
        VkPipelineShaderStageCreateInfo stages[2]{};
        for(int stage=0;stage<2;++stage) {
            auto code=shader(!stage,linear);VkShaderModuleCreateInfo ci{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};ci.codeSize=code.words.size()*4;ci.pCode=code.words.data();
            check(vkCreateShaderModule(device,&ci,nullptr,&modules[linear*2+stage]));stages[stage].sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
            stages[stage].stage=stage?VK_SHADER_STAGE_FRAGMENT_BIT:VK_SHADER_STAGE_VERTEX_BIT;stages[stage].module=modules[linear*2+stage];stages[stage].pName="main";
        }
        VkGraphicsPipelineCreateInfo pc{VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO};pc.pNext=&rendering;pc.stageCount=2;pc.pStages=stages;
        pc.pVertexInputState=&vi;pc.pInputAssemblyState=&ia;pc.pViewportState=&vp;pc.pRasterizationState=&raster;pc.pMultisampleState=&ms;pc.pColorBlendState=&cb;pc.layout=layout;
        check(vkCreateGraphicsPipelines(device,VK_NULL_HANDLE,1,&pc,nullptr,&pipelines[linear]));
    }
    VkCommandPoolCreateInfo pool_ci{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pool_ci.queueFamilyIndex=family;pool_ci.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    VkCommandPool pool;check(vkCreateCommandPool(device,&pool_ci,nullptr,&pool));VkCommandBufferAllocateInfo command_ci{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};command_ci.commandPool=pool;command_ci.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;command_ci.commandBufferCount=1;
    VkCommandBuffer command;check(vkAllocateCommandBuffers(device,&command_ci,&command));int failed=0;
    for(int clipped=0;clipped<2;++clipped)for(int linear=0;linear<2;++linear) {
        float data[]={-1,-1,.5f,1,0, clipped?6.f:2.f,-2,1,2,1, -4,clipped?12.f:4.f,2,4,2};std::memcpy(vertices.mapped,data,sizeof(data));
        check(vkResetCommandBuffer(command,0));VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};check(vkBeginCommandBuffer(command,&begin));
        VkImageMemoryBarrier barrier{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};barrier.oldLayout=VK_IMAGE_LAYOUT_UNDEFINED;barrier.newLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        barrier.srcQueueFamilyIndex=barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;barrier.image=image;barrier.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};barrier.dstAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,0,0,nullptr,0,nullptr,1,&barrier);
        VkRenderingAttachmentInfo color{VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO};color.imageView=view;color.imageLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;color.loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR;color.storeOp=VK_ATTACHMENT_STORE_OP_STORE;
        VkRenderingInfo info{VK_STRUCTURE_TYPE_RENDERING_INFO};info.renderArea=scissor;info.layerCount=1;info.colorAttachmentCount=1;info.pColorAttachments=&color;
        vkCmdBeginRendering(command,&info);vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_GRAPHICS,pipelines[linear]);VkDeviceSize offset=0;vkCmdBindVertexBuffers(command,0,1,&vertices.handle,&offset);vkCmdDraw(command,3,1,0,0);vkCmdEndRendering(command);
        barrier.oldLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;barrier.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;barrier.srcAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;barrier.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
        vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&barrier);
        VkBufferImageCopy copy{};copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1};copy.imageExtent={W,H,1};vkCmdCopyImageToBuffer(command,image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,readback.handle,1,&copy);
        VkMemoryBarrier host{VK_STRUCTURE_TYPE_MEMORY_BARRIER};host.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;host.dstAccessMask=VK_ACCESS_HOST_READ_BIT;vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&host,0,nullptr,0,nullptr);
        check(vkEndCommandBuffer(command));VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.commandBufferCount=1;submit.pCommandBuffers=&command;check(vkQueueSubmit(queue,1,&submit,VK_NULL_HANDLE));check(vkQueueWaitIdle(queue));
        auto pixels=static_cast<unsigned char*>(readback.mapped);uint32_t mismatches=0,covered=0,max_error=0;
        for(uint32_t y=0;y<H;++y)for(uint32_t x=0;x<W;++x) {
            auto p=pixels+4*(y*W+x);if(!p[3])continue;++covered;
            double a=(x+.5)/(clipped?32:16),b=(y+.5)/(clipped?32:16);
            double expected=linear?a+2*b:(a/2+b/2)/(1-a-b+a/2+b/4);
            int code=int(std::lround(expected/3*255));uint32_t error=uint32_t(std::abs(int(p[0])-code));
            if(error>1)++mismatches;max_error=std::max(max_error,error);
        }
        std::printf("CASE {\"clipped\":%s,\"noperspective\":%s,\"covered\":%u,\"mismatches\":%u,\"max_code_error\":%u}\n",clipped?"true":"false",linear?"true":"false",covered,mismatches,max_error);std::fflush(stdout);
        failed+=mismatches!=0 || (clipped ? covered!=256u : covered!=120u && covered!=136u);
    }
    check(vkDeviceWaitIdle(device));vkDestroyCommandPool(device,pool,nullptr);for(auto p:pipelines)vkDestroyPipeline(device,p,nullptr);
    for(auto m:modules)vkDestroyShaderModule(device,m,nullptr);vkDestroyPipelineLayout(device,layout,nullptr);vkDestroyImageView(device,view,nullptr);vkDestroyImage(device,image,nullptr);vkFreeMemory(device,image_memory,nullptr);
    for(auto b:{vertices,readback}){vkUnmapMemory(device,b.memory);vkDestroyBuffer(device,b.handle,nullptr);vkFreeMemory(device,b.memory,nullptr);}
    vkDestroyDevice(device,nullptr);vkDestroyInstance(instance,nullptr);
    std::printf("TERMINAL failures=%d device_waited=true objects_destroyed=true\n",failed);return failed?1:0;
} catch(const std::exception& e) {std::fprintf(stderr,"ERROR %s\n",e.what());return 2;}
