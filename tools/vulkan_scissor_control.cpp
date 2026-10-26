// SPDX-License-Identifier: AGPL-3.0-only
// Independent bounded raster/resolve diagnostic. No VisPy or Dawn linkage.
#include <vulkan/vulkan.h>
#include <spirv/unified1/spirv.hpp11>
#include <vector>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>

void check(VkResult r) { if (r != VK_SUCCESS) throw std::runtime_error("Vulkan result " + std::to_string(r)); }
struct Spirv {
    std::vector<uint32_t> w{0x07230203,0x00010000,0,64,0};
    void op(spv::Op code, std::initializer_list<uint32_t> args) {
        w.push_back((uint32_t(args.size()+1)<<16)|uint32_t(code)); w.insert(w.end(),args);
    }
};
// Explicit minimal shaders: vertex vec2 -> position vec4; constant red fragment.
// IDs are local to each module; no translator, geometry clipping or discard.
Spirv shader(bool vertex) {
    Spirv s;
    s.op(spv::Op::OpCapability,{uint32_t(spv::Capability::Shader)});
    s.op(spv::Op::OpMemoryModel,{0,1});
    if (vertex) s.op(spv::Op::OpEntryPoint,{0,20,0x6e69616d,0,10,11});
    else { s.op(spv::Op::OpEntryPoint,{4,20,0x6e69616d,0,11}); s.op(spv::Op::OpExecutionMode,{20,7}); }
    if (vertex) { s.op(spv::Op::OpDecorate,{10,30,0}); s.op(spv::Op::OpDecorate,{11,11,0}); }
    else s.op(spv::Op::OpDecorate,{11,30,0});
    s.op(spv::Op::OpTypeVoid,{1});s.op(spv::Op::OpTypeFunction,{2,1});
    s.op(spv::Op::OpTypeFloat,{3,32});s.op(spv::Op::OpTypeVector,{4,3,2});s.op(spv::Op::OpTypeVector,{5,3,4});
    s.op(spv::Op::OpTypePointer,{6,1,4});s.op(spv::Op::OpTypePointer,{7,3,5});
    s.op(spv::Op::OpConstant,{3,8,0});s.op(spv::Op::OpConstant,{3,9,0x3f800000});
    if (vertex) s.op(spv::Op::OpVariable,{6,10,1});
    s.op(spv::Op::OpVariable,{7,11,3});
    if (!vertex) s.op(spv::Op::OpConstantComposite,{5,12,9,8,8,9});
    s.op(spv::Op::OpFunction,{1,20,0,2});s.op(spv::Op::OpLabel,{21});
    if (vertex) {
        s.op(spv::Op::OpLoad,{4,22,10});s.op(spv::Op::OpCompositeExtract,{3,23,22,0});
        s.op(spv::Op::OpCompositeExtract,{3,24,22,1});s.op(spv::Op::OpCompositeConstruct,{5,25,23,24,8,9});
        s.op(spv::Op::OpStore,{11,25});
    } else s.op(spv::Op::OpStore,{11,12});
    s.op(spv::Op::OpReturn,{});s.op(spv::Op::OpFunctionEnd,{});return s;
}
struct Image { VkImage image{};VkDeviceMemory memory{};VkImageView view{}; };
struct Buffer { VkBuffer buffer{};VkDeviceMemory memory{};void* mapped{}; };
int main() try {
    constexpr uint32_t W=301,H=177;
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.apiVersion=VK_API_VERSION_1_3;
    VkInstanceCreateInfo ic{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};ic.pApplicationInfo=&app;
    VkInstance instance;check(vkCreateInstance(&ic,nullptr,&instance));
    uint32_t n=0;check(vkEnumeratePhysicalDevices(instance,&n,nullptr));
    std::vector<VkPhysicalDevice> physical(n);check(vkEnumeratePhysicalDevices(instance,&n,physical.data()));
    if (!n) throw std::runtime_error("no device");auto gpu=physical[0];
    VkPhysicalDeviceProperties props;vkGetPhysicalDeviceProperties(gpu,&props);
    std::printf("DEVICE %s api=%u driver=%u\n",props.deviceName,props.apiVersion,props.driverVersion);
    vkGetPhysicalDeviceQueueFamilyProperties(gpu,&n,nullptr);std::vector<VkQueueFamilyProperties> families(n);
    vkGetPhysicalDeviceQueueFamilyProperties(gpu,&n,families.data());uint32_t family=0;
    while (family<n && !(families[family].queueFlags&VK_QUEUE_GRAPHICS_BIT)) ++family;
    if (family==n) throw std::runtime_error("no graphics queue");
    float priority=1;VkDeviceQueueCreateInfo qc{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qc.queueFamilyIndex=family;qc.queueCount=1;qc.pQueuePriorities=&priority;
    VkPhysicalDeviceDynamicRenderingFeatures dynamic{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DYNAMIC_RENDERING_FEATURES};dynamic.dynamicRendering=VK_TRUE;
    VkDeviceCreateInfo dc{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};dc.pNext=&dynamic;dc.queueCreateInfoCount=1;dc.pQueueCreateInfos=&qc;
    VkDevice device;check(vkCreateDevice(gpu,&dc,nullptr,&device));VkQueue queue;vkGetDeviceQueue(device,family,0,&queue);
    VkPhysicalDeviceMemoryProperties mp;vkGetPhysicalDeviceMemoryProperties(gpu,&mp);
    auto allocate=[&](VkMemoryRequirements req,VkMemoryPropertyFlags flags) {
        uint32_t i=0;for(;i<mp.memoryTypeCount;++i)if((req.memoryTypeBits&(1u<<i))&&(mp.memoryTypes[i].propertyFlags&flags)==flags)break;
        if(i==mp.memoryTypeCount)throw std::runtime_error("no memory type");
        VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ai.allocationSize=req.size;ai.memoryTypeIndex=i;
        VkDeviceMemory mem;check(vkAllocateMemory(device,&ai,nullptr,&mem));return mem;
    };
    auto makeImage=[&](VkSampleCountFlagBits samples) {
        Image a;VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};ci.imageType=VK_IMAGE_TYPE_2D;ci.format=VK_FORMAT_R8G8B8A8_UNORM;
        ci.extent={W,H,1};ci.mipLevels=1;ci.arrayLayers=1;ci.samples=samples;ci.tiling=VK_IMAGE_TILING_OPTIMAL;
        ci.usage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT;ci.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
        check(vkCreateImage(device,&ci,nullptr,&a.image));VkMemoryRequirements req;vkGetImageMemoryRequirements(device,a.image,&req);
        a.memory=allocate(req,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);check(vkBindImageMemory(device,a.image,a.memory,0));
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};vi.image=a.image;vi.viewType=VK_IMAGE_VIEW_TYPE_2D;vi.format=ci.format;vi.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        check(vkCreateImageView(device,&vi,nullptr,&a.view));return a;
    };
    auto makeBuffer=[&](VkDeviceSize size,VkBufferUsageFlags usage) {
        Buffer b;VkBufferCreateInfo ci{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};ci.size=size;ci.usage=usage;ci.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
        check(vkCreateBuffer(device,&ci,nullptr,&b.buffer));VkMemoryRequirements req;vkGetBufferMemoryRequirements(device,b.buffer,&req);
        b.memory=allocate(req,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);check(vkBindBufferMemory(device,b.buffer,b.memory,0));
        check(vkMapMemory(device,b.memory,0,VK_WHOLE_SIZE,0,&b.mapped));return b;
    };
    auto multi=makeImage(VK_SAMPLE_COUNT_4_BIT),resolved=makeImage(VK_SAMPLE_COUNT_1_BIT);
    auto vertices=makeBuffer(6*sizeof(float),VK_BUFFER_USAGE_VERTEX_BUFFER_BIT),readback=makeBuffer(W*H*4,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    const float triangle[]={-1,-1,3,-1,-1,3};std::memcpy(vertices.mapped,triangle,sizeof(triangle));
    VkShaderModule modules[2];for(int i=0;i<2;++i){auto s=shader(i==0);VkShaderModuleCreateInfo ci{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};ci.codeSize=s.w.size()*4;ci.pCode=s.w.data();check(vkCreateShaderModule(device,&ci,nullptr,&modules[i]));}
    VkPipelineLayoutCreateInfo lc{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};VkPipelineLayout layout;check(vkCreatePipelineLayout(device,&lc,nullptr,&layout));
    VkAttachmentDescription attachments[2]{};
    for(int i=0;i<2;++i){attachments[i].format=VK_FORMAT_R8G8B8A8_UNORM;attachments[i].samples=i?VK_SAMPLE_COUNT_1_BIT:VK_SAMPLE_COUNT_4_BIT;attachments[i].loadOp=i?VK_ATTACHMENT_LOAD_OP_DONT_CARE:VK_ATTACHMENT_LOAD_OP_CLEAR;attachments[i].storeOp=VK_ATTACHMENT_STORE_OP_STORE;attachments[i].stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE;attachments[i].stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE;attachments[i].initialLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;attachments[i].finalLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;}
    VkAttachmentReference color{0,VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL},resolve{1,VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
    VkSubpassDescription sub{};sub.pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS;sub.colorAttachmentCount=1;sub.pColorAttachments=&color;sub.pResolveAttachments=&resolve;
    VkRenderPassCreateInfo rc{VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO};rc.attachmentCount=2;rc.pAttachments=attachments;rc.subpassCount=1;rc.pSubpasses=&sub;
    VkRenderPass pass;check(vkCreateRenderPass(device,&rc,nullptr,&pass));
    VkImageView views[]={multi.view,resolved.view};VkFramebufferCreateInfo fc{VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO};fc.renderPass=pass;fc.attachmentCount=2;fc.pAttachments=views;fc.width=W;fc.height=H;fc.layers=1;
    VkFramebuffer frame;check(vkCreateFramebuffer(device,&fc,nullptr,&frame));
    VkPipelineShaderStageCreateInfo stages[2]{};for(int i=0;i<2;++i){stages[i].sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;stages[i].stage=i?VK_SHADER_STAGE_FRAGMENT_BIT:VK_SHADER_STAGE_VERTEX_BIT;stages[i].module=modules[i];stages[i].pName="main";}
    VkVertexInputBindingDescription binding{0,2*sizeof(float),VK_VERTEX_INPUT_RATE_VERTEX};VkVertexInputAttributeDescription attr{0,0,VK_FORMAT_R32G32_SFLOAT,0};
    VkPipelineVertexInputStateCreateInfo vi{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};vi.vertexBindingDescriptionCount=1;vi.pVertexBindingDescriptions=&binding;vi.vertexAttributeDescriptionCount=1;vi.pVertexAttributeDescriptions=&attr;
    VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};ia.topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    VkPipelineViewportStateCreateInfo vp{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};vp.viewportCount=1;vp.scissorCount=1;
    VkPipelineRasterizationStateCreateInfo raster{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO};raster.polygonMode=VK_POLYGON_MODE_FILL;raster.cullMode=VK_CULL_MODE_NONE;raster.frontFace=VK_FRONT_FACE_COUNTER_CLOCKWISE;raster.lineWidth=1;
    VkPipelineMultisampleStateCreateInfo ms{VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO};ms.rasterizationSamples=VK_SAMPLE_COUNT_4_BIT;
    VkPipelineColorBlendAttachmentState blend{};blend.colorWriteMask=15;
    VkPipelineColorBlendStateCreateInfo cb{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};cb.attachmentCount=1;cb.pAttachments=&blend;
    VkDynamicState states[]={VK_DYNAMIC_STATE_VIEWPORT,VK_DYNAMIC_STATE_SCISSOR};VkPipelineDynamicStateCreateInfo ds{VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO};ds.dynamicStateCount=2;ds.pDynamicStates=states;
    VkFormat format=VK_FORMAT_R8G8B8A8_UNORM;VkPipelineRenderingCreateInfo rendering{VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO};rendering.colorAttachmentCount=1;rendering.pColorAttachmentFormats=&format;
    VkPipeline pipelines[2];for(int d=0;d<2;++d){VkGraphicsPipelineCreateInfo pc{VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO};pc.pNext=d?&rendering:nullptr;pc.stageCount=2;pc.pStages=stages;pc.pVertexInputState=&vi;pc.pInputAssemblyState=&ia;pc.pViewportState=&vp;pc.pRasterizationState=&raster;pc.pMultisampleState=&ms;pc.pColorBlendState=&cb;pc.pDynamicState=&ds;pc.layout=layout;pc.renderPass=d?VK_NULL_HANDLE:pass;check(vkCreateGraphicsPipelines(device,VK_NULL_HANDLE,1,&pc,nullptr,&pipelines[d]));}
    VkCommandPoolCreateInfo poolci{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};poolci.queueFamilyIndex=family;poolci.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    VkCommandPool pool;check(vkCreateCommandPool(device,&poolci,nullptr,&pool));VkCommandBufferAllocateInfo ac{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ac.commandPool=pool;ac.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ac.commandBufferCount=1;
    VkCommandBuffer command;check(vkAllocateCommandBuffers(device,&ac,&command));
    int failed=0;
    for(int d=0;d<2;++d)for(int right=0;right<2;++right){
        check(vkResetCommandBuffer(command,0));VkCommandBufferBeginInfo bc{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};check(vkBeginCommandBuffer(command,&bc));
        VkImageMemoryBarrier barriers[2]{};for(int i=0;i<2;++i){auto& b=barriers[i];b.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;b.oldLayout=VK_IMAGE_LAYOUT_UNDEFINED;b.newLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;b.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;b.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;b.image=i?resolved.image:multi.image;b.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};b.dstAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;}
        vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,0,0,nullptr,0,nullptr,2,barriers);
        VkClearValue black{};black.color.float32[3]=1;
        if(d){VkRenderingAttachmentInfo a{VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO};a.imageView=multi.view;a.imageLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;a.resolveMode=VK_RESOLVE_MODE_AVERAGE_BIT;a.resolveImageView=resolved.view;a.resolveImageLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;a.loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR;a.storeOp=VK_ATTACHMENT_STORE_OP_STORE;a.clearValue=black;VkRenderingInfo info{VK_STRUCTURE_TYPE_RENDERING_INFO};info.renderArea={{0,0},{W,H}};info.layerCount=1;info.colorAttachmentCount=1;info.pColorAttachments=&a;vkCmdBeginRendering(command,&info);}
        else {VkClearValue clears[]={black,black};VkRenderPassBeginInfo info{VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO};info.renderPass=pass;info.framebuffer=frame;info.renderArea={{0,0},{W,H}};info.clearValueCount=2;info.pClearValues=clears;vkCmdBeginRenderPass(command,&info,VK_SUBPASS_CONTENTS_INLINE);}
        VkViewport viewport{0,float(H),float(W),-float(H),0,1};VkRect2D scissor{{right?150:0,0},{right?151u:150u,H}};
        vkCmdSetViewport(command,0,1,&viewport);vkCmdSetScissor(command,0,1,&scissor);vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_GRAPHICS,pipelines[d]);VkDeviceSize offset=0;vkCmdBindVertexBuffers(command,0,1,&vertices.buffer,&offset);vkCmdDraw(command,3,1,0,0);
        if(d)vkCmdEndRendering(command);else vkCmdEndRenderPass(command);
        auto b=barriers[1];b.oldLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;b.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;b.srcAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;b.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
        vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&b);
        VkBufferImageCopy copy{};copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1};copy.imageExtent={W,H,1};vkCmdCopyImageToBuffer(command,resolved.image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,readback.buffer,1,&copy);
        VkMemoryBarrier host{VK_STRUCTURE_TYPE_MEMORY_BARRIER};host.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;host.dstAccessMask=VK_ACCESS_HOST_READ_BIT;vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&host,0,nullptr,0,nullptr);
        check(vkEndCommandBuffer(command));VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.commandBufferCount=1;submit.pCommandBuffers=&command;check(vkQueueSubmit(queue,1,&submit,VK_NULL_HANDLE));check(vkQueueWaitIdle(queue));
        auto pixels=static_cast<unsigned char*>(readback.mapped);unsigned mismatches=0,first=0;
        for(uint32_t y=0;y<H;++y)for(uint32_t x=0;x<W;++x){auto p=pixels+4*(y*W+x);bool red=right?x>=150:x<150;if(p[0]!=(red?255:0)||p[1]||p[2]||p[3]!=255){if(!mismatches)first=y*W+x;++mismatches;}}
        auto p=pixels+first*4;std::printf("CASE {\"dynamic\":%s,\"right\":%s,\"samples\":4,\"mismatched_pixels\":%u,\"first_xy\":[%u,%u],\"first_rgba\":[%u,%u,%u,%u]}\n",d?"true":"false",right?"true":"false",mismatches,first%W,first/W,p[0],p[1],p[2],p[3]);std::fflush(stdout);failed+=mismatches!=0;
    }
    check(vkDeviceWaitIdle(device));vkDestroyCommandPool(device,pool,nullptr);for(auto p:pipelines)vkDestroyPipeline(device,p,nullptr);vkDestroyFramebuffer(device,frame,nullptr);vkDestroyRenderPass(device,pass,nullptr);vkDestroyPipelineLayout(device,layout,nullptr);for(auto m:modules)vkDestroyShaderModule(device,m,nullptr);
    for(auto a:{multi,resolved}){vkDestroyImageView(device,a.view,nullptr);vkDestroyImage(device,a.image,nullptr);vkFreeMemory(device,a.memory,nullptr);}for(auto b:{vertices,readback}){vkUnmapMemory(device,b.memory);vkDestroyBuffer(device,b.buffer,nullptr);vkFreeMemory(device,b.memory,nullptr);}vkDestroyDevice(device,nullptr);vkDestroyInstance(instance,nullptr);
    std::printf("TERMINAL cases=4 failures=%d device_waited=true objects_destroyed=true\n",failed);return failed?1:0;
} catch(const std::exception& e) {std::fprintf(stderr,"ERROR %s\n",e.what());return 2;}
