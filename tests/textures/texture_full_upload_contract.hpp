// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include "runtime_texture.hpp"
#include "texture_preparation_legacy_reference.hpp"
#include <type_traits>
#include <utility>
#include <iostream>

namespace vispy::texture_contracts {
namespace upload = vispy::textures;
template<class T> concept preparable = requires(T&& value) {upload::prepare_full_upload(std::forward<T>(value));};
static_assert(!preparable<TextureData> && !preparable<const TextureData>);
static_assert(preparable<TextureData&> && preparable<const TextureData&>);
static_assert(!std::is_copy_constructible_v<upload::FullUpload> && std::is_move_constructible_v<upload::FullUpload>);
namespace {
size_t cases=0, borrowed=0, fallback=0, rejections=0, aligned=0, padded=0;
void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
bool same_descriptor(const PreparedTexture& a,const PreparedTexture& b) {
    return a.format==b.format && a.dimension==b.dimension && a.view_dimension==b.view_dimension &&
        a.sample_type==b.sample_type && a.texel_size==b.texel_size && a.channels==b.channels &&
        a.requires_float32_filterable==b.requires_float32_filterable && a.requires_unorm16==b.requires_unorm16;
}
std::vector<uint8_t> old_rows(const PreparedTexture& prepared,const TextureData& data) {
    const uint32_t bytes=static_cast<uint32_t>(data.width*prepared.texel_size);
    const uint32_t pitch=(bytes+255u)&~255u;
    std::vector<uint8_t> rows(static_cast<size_t>(pitch)*data.height*data.depth,0);
    for(int z=0;z<data.depth;++z) for(int y=0;y<data.height;++y) {
        const size_t row=static_cast<size_t>(z)*data.height+y;
        std::memcpy(rows.data()+row*pitch,prepared.bytes.data()+row*bytes,bytes);
    }
    return rows;
}
void fill(TextureData& data) {
    const size_t n=texture_detail::texels(data)*data.channels;
    const size_t component=texture_detail::dtype_size(data.dtype);
    data.pixels.resize(n*component);
    const uint32_t bits[]={0x7fc12345,0xffc00001,0x7f800001,0x80000000,0x00000001,0x7f800000,0xff800000,0x3f000000};
    for(size_t i=0;i<n;++i) {
        auto* p=data.pixels.data()+i*component;
        if(data.dtype=="f32") std::memcpy(p,&bits[i%8],4);
        else if(data.dtype=="f64") {double v=(i%2 ? -1.0 : .125)*static_cast<double>(i%257);std::memcpy(p,&v,8);}
        else if(data.dtype=="f16") {uint16_t v=texture_detail::float_to_half(static_cast<float>(i%17)*.1f);std::memcpy(p,&v,2);}
        else for(size_t b=0;b<component;++b) p[b]=static_cast<uint8_t>((i*31+b*73)%256);
    }
}
void compare(TextureData& data,const TextureData* allocation=nullptr) {
    ++cases;
    auto original=data.pixels;
    PreparedTexture expected;upload::FullUpload actual;
    std::string old_error,new_error;
    try {expected=legacy_prepare_texture(data,allocation);} catch(const std::runtime_error& e){old_error=e.what();}
    try {actual=upload::prepare_full_upload(data,allocation);} catch(const std::runtime_error& e){new_error=e.what();}
    require(old_error==new_error,"exception mismatch");
    if(!old_error.empty()){++rejections;require(data.pixels==original,"rejected source changed");return;}
    require(same_descriptor(expected,actual.prepared()),"descriptor mismatch");
    require(actual.size()==expected.bytes.size(),"logical byte count mismatch");
    require(std::equal(expected.bytes.begin(),expected.bytes.end(),actual.data()),"logical bytes mismatch");
    if(actual.is_borrowed()) {
        ++borrowed;require(actual.data()==data.pixels.data(),"source not borrowed exactly");
        require(actual.prepared().bytes.empty(),"borrowed source materialized");
    } else {++fallback;require(actual.prepared().bytes==expected.bytes,"fallback mismatch");}
    // Accessors must remain valid after moving both borrowed and owned views.
    auto moved=std::move(actual);
    const auto rows=old_rows(expected,data);
    size_t calls=0;
    upload::with_upload_rows(moved,[&](const PreparedTexture& descriptor,const uint8_t* bytes,size_t size,uint32_t pitch,int height) {
        ++calls;require(same_descriptor(expected,descriptor),"row descriptor mismatch");
        require(size==rows.size() && pitch==((data.width*expected.texel_size+255u)&~255u) && height==data.height,"row layout mismatch");
        require(std::equal(rows.begin(),rows.end(),bytes),"padded upload bytes mismatch");
        if(pitch==data.width*expected.texel_size){++aligned;require(bytes==moved.data(),"aligned rows copied");}
        else {++padded;require(bytes!=moved.data(),"unaligned rows not packed");}
    });
    require(calls==1 && data.pixels==original,"source changed or consumer repeated");
}
void matrix() {
    for(const auto* dtype:{"u8","i8","u16","i16","u32","i32","f16","f32","f64"})
    for(const auto* format:{"red","rg","rgb","rgba","luminance","luminance_alpha","alpha"})
    for(int width:{1,3,63,64,65,256}) for(int dimension:{1,2,3})
    for(const auto* suffix:{"","32f","16f","8","16","32ui","32i","16ui","8i","8ui","16i"}) {
        TextureData data;data.dtype=dtype;data.format=format;data.channels=texture_detail::format_channels(format);
        data.width=width;data.height=dimension>=2?3:1;data.depth=dimension==3?2:1;data.dimensions=dimension;
        std::string base=data.channels==1?"r":data.channels==2?"rg":data.channels==3?"rgb":"rgba";
        data.internal_format=std::string(suffix).empty()?"":base+suffix;
        data.min_filter=data.mag_filter=width%2?"linear":"nearest";
        fill(data);compare(data);
        if(width==1){data.pixels.clear();compare(data);}
    }
    // A separate allocation may retain a different storage dtype.
    for(const auto* source:{"f32","f64","u8","u16","u32","i32"})
    for(const auto* storage:{"r32f","r16f","r8","r16","r32ui","r32i"}) {
        TextureData data;data.width=65;data.channels=1;data.format="red";data.dtype=source;fill(data);
        TextureData allocation=data;allocation.pixels.clear();allocation.dtype="u8";allocation.internal_format=storage;
        compare(data,&allocation);
    }
    TextureData valid;valid.width=64;valid.channels=1;valid.format="red";valid.dtype="f32";valid.internal_format="r32f";fill(valid);
    for(int change=0;change<13;++change) {
        auto data=valid;auto allocation=valid;
        switch(change) {
        case 0:data.width=0;break;case 1:data.dimensions=4;break;case 2:data.channels=0;break;
        case 3:data.format="invalid";break;case 4:data.dtype="invalid";break;case 5:allocation.internal_format="invalid";break;
        case 6:data.pixels.pop_back();break;case 7:allocation.channels=2;break;case 8:allocation.dimensions=3;break;
        case 9:data.width=INT32_MAX;data.height=INT32_MAX;data.depth=INT32_MAX;data.dimensions=3;data.pixels.clear();break;
        case 10:data.dimensions=1;data.height=2;break;case 11:data.depth=2;break;case 12:data.channels=5;break;
        }
        const auto before=rejections;compare(data,&allocation);require(rejections==before+1,"invalid input accepted");
    }
    auto overflow=valid;overflow.dimensions=3;overflow.width=overflow.height=overflow.depth=INT32_MAX;overflow.pixels.clear();
    const auto before_overflow=rejections;compare(overflow);require(rejections==before_overflow+1,"extent overflow accepted");
    // A live view observes same-storage edits; resizing is rejected before consumption.
    auto live=valid;auto upload=upload::prepare_full_upload(live);
    const auto first=live.pixels[0];live.pixels[0]^=1;
    upload::with_upload_rows(upload,[&](const PreparedTexture&,const uint8_t* bytes,size_t,uint32_t,int){require(bytes[0]==(first^1),"live borrow did not observe source");});
    live.pixels.push_back(0);
    bool rejected_resize=false;
    try {upload::with_upload_rows(upload,[](const PreparedTexture&,const uint8_t*,size_t,uint32_t,int){throw std::logic_error("resized source reached consumer");});}
    catch(const std::runtime_error& error){rejected_resize=std::string(error.what())=="texture: borrowed upload source storage changed";}
    require(rejected_resize,"borrow resize not rejected");
    require(borrowed>0 && fallback>0 && rejections>0 && aligned>0 && padded>0,"matrix missed a required branch");
}

} // anonymous namespace
inline void full_upload_equivalence_contract() {
    matrix();
    require(cases==14603,"full upload equivalence matrix incomplete");
    std::cout << "full upload equivalence cases=" << cases << " borrowed=" << borrowed
              << " fallback=" << fallback << " rejected=" << rejections << " GPU_used=false\n";
}
} // namespace vispy::texture_contracts
