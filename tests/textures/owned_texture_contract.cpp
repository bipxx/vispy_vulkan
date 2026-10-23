// SPDX-License-Identifier: AGPL-3.0-only
#include "runtime_owned_texture.hpp"
#include <array>
#include <iostream>
#include <stdexcept>
using vispy::textures::apply_owned_texture_data;
namespace {
size_t cases=0,transfers=0,partials=0,failures=0;
void require(bool condition,const char* text){if(!condition)throw std::runtime_error(text);}
bool same(const TextureData& a,const TextureData& b){return a.pixels==b.pixels&&a.dtype==b.dtype&&a.width==b.width&&a.height==b.height&&a.depth==b.depth&&a.channels==b.channels&&a.format==b.format&&a.internal_format==b.internal_format&&a.dimensions==b.dimensions&&a.min_filter==b.min_filter&&a.mag_filter==b.mag_filter;}
bool same(const PreparedTexture& a,const PreparedTexture& b){return a.bytes==b.bytes&&a.format==b.format&&a.dimension==b.dimension&&a.view_dimension==b.view_dimension&&a.sample_type==b.sample_type&&a.texel_size==b.texel_size&&a.channels==b.channels&&a.requires_float32_filterable==b.requires_float32_filterable&&a.requires_unorm16==b.requires_unorm16;}
std::vector<int> shape(const TextureData& data){auto result=data.dimensions==1?std::vector<int>{data.width}:data.dimensions==2?std::vector<int>{data.height,data.width}:std::vector<int>{data.depth,data.height,data.width};result.push_back(data.channels);return result;}
ByteBlob make_blob(std::vector<int> extent,const std::string& dtype){
    ByteBlob blob;blob.shape=extent;blob.dtype=dtype;size_t count=1;for(int x:extent)count*=x;
    const auto unit=texture_detail::dtype_size(dtype);blob.bytes.resize(count*unit);
    for(size_t i=0;i<count;++i){
        uint64_t bits=(i*65537u+17u);
        if(dtype=="f16"){constexpr uint16_t values[]={0,0x8000,1,0x3c00,0x7c00,0xfc00,0x7e01};bits=values[i%7];}
        if(dtype=="f32"){constexpr uint32_t values[]={0,0x80000000u,1,0x3f800000u,0x7f800000u,0xff800000u,0x7fc12345u};bits=values[i%7];}
        if(dtype=="f64"){constexpr uint64_t values[]={0,0x8000000000000000ull,1,0x3ff0000000000000ull,0x7ff0000000000000ull,0xfff0000000000000ull,0x7ff8123456789abcull};bits=values[i%7];}
        std::memcpy(blob.bytes.data()+i*unit,&bits,unit);
    }
    return blob;
}
void compare(TextureData original,ByteBlob upload,const std::vector<int>& offset,bool full,bool valid=true){
    const auto resident=original;auto expected=original;auto actual=original;const auto immutable=upload;auto owned=upload;
    const auto* address=owned.bytes.data();const auto old_shape=owned.shape;const auto old_dtype=owned.dtype;
    std::string before_error,after_error;
    try{apply_texture_data(expected,immutable,offset,&resident);}catch(const std::runtime_error& e){before_error=e.what();}
    bool transferred=false;try{transferred=apply_owned_texture_data(actual,owned,offset,true,&resident);}catch(const std::runtime_error& e){after_error=e.what();}
    require(transferred==(full&&valid),"transfer result differs from actual ownership");
    require(before_error==after_error,"validation error identity changed");require(same(actual,expected),"owned DATA result differs from canonical const helper");
    require(immutable.bytes==upload.bytes&&immutable.shape==upload.shape&&immutable.dtype==upload.dtype,"const upload was changed");
    require(owned.shape==old_shape&&owned.dtype==old_dtype,"owned nonpayload metadata was changed");
    require(valid==before_error.empty(),"case validity expectation differs");
    if(!before_error.empty()){require(same(actual,original)&&owned.bytes==upload.bytes,"validation failure changed source or resident");++failures;}
    else{
        require(same(prepare_texture(actual,&resident),prepare_texture(expected,&resident)),"prepared descriptor/bytes changed");
        if(full){require(actual.pixels.data()==address,"complete owned DATA copied rather than transferred");++transfers;
            owned.bytes.assign(upload.bytes.size(),255);require(actual.pixels==upload.bytes,"reuse of consumed source changed texture");}
        else{require(owned.bytes==upload.bytes,"partial fallback consumed source");++partials;}
    }
    require(same(resident,original),"previous revision/source allocation was changed");++cases;
}
}
int main(){try{
    const std::array<std::string,9> dtypes={"u8","i8","u16","i16","u32","i32","f16","f32","f64"};
    const char* formats[]={"red","rg","rgb","rgba"};
    for(int dimensions:{1,2,3})for(int channels:{1,2,3,4})for(int width:{4,65})for(const auto& dtype:dtypes){
        TextureData data;data.dimensions=dimensions;data.width=width;data.height=dimensions>=2?2:1;data.depth=dimensions==3?3:1;data.channels=channels;data.format=formats[channels-1];data.internal_format=channels==1?"r32f":channels==2?"rg32f":channels==3?"rgb32f":"rgba32f";data.dtype="f32";
        data.pixels=make_blob(shape(data),"f32").bytes;
        compare(data,make_blob(shape(data),dtype),std::vector<int>(dimensions,0),true);
        auto region=shape(data);for(int i=0;i<dimensions-1;++i)region[i]=1;region[dimensions-1]=width-2;std::vector<int> offset(dimensions,0);offset.back()=1;
        compare(data,make_blob(region,dtype),offset,false);
    }
    TextureData small;small.width=4;small.height=3;small.channels=1;small.dtype="u8";small.format="red";small.pixels.assign(12,7);
    const auto valid=make_blob(shape(small),"u8");
    for(int variant=0;variant<10;++variant){auto data=small;auto blob=valid;std::vector<int> offset{0,0};
        if(variant==0)blob.shape.pop_back();if(variant==1)offset.pop_back();if(variant==2)blob.shape.back()=2;if(variant==3)offset[0]=-1;
        if(variant==4)blob.shape[0]=0;if(variant==5)offset[1]=5;if(variant==6)blob.bytes.pop_back();if(variant==7)blob.dtype="unsupported";
        if(variant==8)data.dimensions=4;if(variant==9)data.width=0;
        compare(data,blob,offset,false,false);
    }
    // A full replacement after mixed-type partial assembly must replace the
    // f64 shadow, while an already captured previous revision stays unchanged.
    auto assembled=small;apply_texture_data(assembled,make_blob({1,2,1},"f32"),{1,1},&small);
    require(assembled.dtype=="f64","mixed setup did not promote shadow");compare(assembled,valid,{0,0},true);
    TextureData large;large.dimensions=3;large.width=large.height=large.depth=256;large.channels=1;large.format="red";large.internal_format="r32f";large.dtype="f32";
    auto input=make_blob(shape(large),"f32");require(input.bytes.size()==67108864,"large payload extent changed");compare(large,input,{0,0,0},true);
    // The canonical runtime's legacy full predicate differs from the helper
    // for ordinary1D uploads. Explicit gate=false must retain those DATA bytes
    // for the unchanged base+updates history; do not silently fix1D routing.
    size_t runtime_gated_cases=0,runtime_1d_fallbacks=0;
    for(int dimensions:{1,1,2,3}){
        TextureData data;data.dimensions=dimensions;data.width=4;data.height=dimensions>=2?3:1;data.depth=dimensions==3?2:1;data.channels=1;data.format="red";data.internal_format="r32f";data.dtype="f32";
        auto payload=make_blob(shape(data),"f32");const auto original_payload=payload;const auto* address=payload.bytes.data();std::vector<int> offset(dimensions,0);
        const bool runtime_full=data.dimensions>=1&&data.dimensions<=3&&
            payload.shape.size()==static_cast<size_t>(data.dimensions+1)&&offset.size()==static_cast<size_t>(data.dimensions)&&
            std::all_of(offset.begin(),offset.end(),[](int value){return value==0;})&&
            payload.shape.size()>=static_cast<size_t>(data.dimensions)&&
            (data.dimensions==3?payload.shape[0]==data.depth&&payload.shape[1]==data.height&&payload.shape[2]==data.width:
                                payload.shape[0]==data.height&&payload.shape[1]==data.width);
        auto canonical=data;apply_texture_data(canonical,original_payload,offset);
        const bool moved=apply_owned_texture_data(data,payload,offset,runtime_full);
        require(moved==runtime_full&&same(data,canonical),"runtime gate changed DATA semantics");
        std::vector<ByteBlob> updates;
        if(!runtime_full)updates.push_back(payload);
        if(dimensions==1){require(!moved&&updates.size()==1&&updates[0].bytes==original_payload.bytes,"1D history lost consumed bytes");++runtime_1d_fallbacks;++partials;}
        else{require(moved&&updates.empty()&&data.pixels.data()==address,"2D/3D runtime full did not transfer");++transfers;}
        ++runtime_gated_cases;++cases;
    }
    size_t malformed_gate_cases=0,legacy_mismatch_cases=0;
    auto guarded_full=[](const TextureData& data,const ByteBlob& payload,const std::vector<int>& offset){
        return data.dimensions>=1&&data.dimensions<=3&&payload.shape.size()==static_cast<size_t>(data.dimensions+1)&&offset.size()==static_cast<size_t>(data.dimensions)&&
            std::all_of(offset.begin(),offset.end(),[](int value){return value==0;})&&
            (data.dimensions==3?payload.shape[0]==data.depth&&payload.shape[1]==data.height&&payload.shape[2]==data.width:
                                payload.shape[0]==data.height&&payload.shape[1]==data.width);
    };
    for(int variant:{0,1,2}){
        TextureData data;data.dimensions=1;data.width=4;data.channels=1;data.format="red";data.dtype="u8";data.pixels.assign(4,17);
        auto payload=make_blob({4,1},"u8");if(variant==0)payload.shape={4};if(variant==1)payload.shape.clear();if(variant==2)data.dimensions=0;
        const auto before=data;const auto old_payload=payload;auto expected=data;std::string first,second;
        try{apply_texture_data(expected,old_payload,{0});}catch(const std::runtime_error& error){first=error.what();}
        const bool permit=guarded_full(data,payload,{0});require(!permit,"invalid metadata received transfer permission");
        try{apply_owned_texture_data(data,payload,{0},permit);}catch(const std::runtime_error& error){second=error.what();}
        require(!first.empty()&&first==second&&same(data,before)&&payload.bytes==old_payload.bytes,"malformed pre-call gate changed error or ownership");
        ++malformed_gate_cases;++failures;++cases;
    }
    for(int width:{2,3,4}){
        TextureData data;data.dimensions=1;data.width=width;data.channels=width;data.format=formats[width-1];data.internal_format=width==2?"rg32f":width==3?"rgb32f":"rgba32f";data.dtype="f32";data.pixels=make_blob(shape(data),"f32").bytes;
        auto payload=make_blob({1,width},"u8");const auto original_payload=payload;auto expected=data;const auto allocation=data;
        apply_texture_data(expected,original_payload,{0},&allocation);
        const bool runtime_full=guarded_full(data,payload,{0});require(runtime_full,"legacy1D mismatch setup changed");
        const bool moved=apply_owned_texture_data(data,payload,{0},runtime_full,&allocation);
        std::vector<ByteBlob> updates;if(!runtime_full)updates.push_back(payload);
        require(!moved&&same(data,expected)&&updates.empty()&&payload.bytes==original_payload.bytes,"legacy1D runtime/helper disagreement changed behavior");
        ++legacy_mismatch_cases;++partials;++cases;
    }
    std::cout<<"{\"status\":\"PASS_OWNED_TEXTURE_DATA_CPU\",\"cases\":"<<cases<<",\"full_address_transfers\":"<<transfers<<",\"partial_unchanged_fallbacks\":"<<partials<<",\"exact_validation_failures\":"<<failures<<",\"runtime_gated_cases\":"<<runtime_gated_cases<<",\"runtime_1d_fallbacks\":"<<runtime_1d_fallbacks<<",\"malformed_gate_cases\":"<<malformed_gate_cases<<",\"legacy_1d_mismatch_cases\":"<<legacy_mismatch_cases<<",\"large_bytes\":67108864,\"GPU_used\":false}\n";
    return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
