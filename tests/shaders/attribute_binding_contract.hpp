// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include "shader/artifact.hpp"
#include <stdexcept>

inline void attribute_binding_contract() {
    auto check=[](bool value,const std::string& message) {
        if (!value) throw std::runtime_error("aggregate attribute: "+message);
    };
    for (uint32_t columns=2; columns<=4; ++columns) for (uint32_t rows=2; rows<=4; ++rows)
        for (const std::vector<uint32_t> shape : {std::vector<uint32_t>{}, {2}, {2,3}}) {
            const std::string type="mat"+std::to_string(columns)+"x"+std::to_string(rows);
            NormAttribute logical{"a",type,1}; logical.array_dimensions=shape;
            AttributeLayout layout;std::string error;
            check(attribute_layout(logical,layout,error),error);
            const uint32_t elements=shape.empty()?1:shape.size()==1?2:6;
            check(layout.locations==elements*columns && layout.record_words==elements*columns*rows,"shape extent");
            const auto tail=attribute_location(layout,layout.locations-1);
            check(tail.type=="vec"+std::to_string(rows) && tail.location==layout.locations,"last location");
            check(tail.binding_views.back().name=="a" && tail.binding_views.back().type==type &&
                tail.binding_views.back().word_offset==layout.record_words-rows &&
                tail.binding_views.back().record_words==layout.record_words,"parent view extent/offset");
            check(tail.binding_views[1].word_offset==(columns-1)*rows &&
                tail.binding_views[1].record_words==columns*rows,"matrix leaf view");
            check(tail.binding_views.front().word_offset==0 && tail.binding_views.front().record_words==rows,"column view");
            if (shape.size()==2) check(tail.binding_views[2].name=="a[1]" &&
                tail.binding_views[2].word_offset==(3*columns-1)*rows &&
                tail.binding_views[2].record_words==3*columns*rows,"subarray view");
            std::string suffix,element;
            for (auto d:shape) { suffix+="["+std::to_string(d)+"]"; element+="["+std::to_string(d-1)+"]"; }
            const std::string expression="a"+element+"["+std::to_string(columns-1)+"]["+std::to_string(rows-1)+"]";
            const auto source="attribute vec4 unused;attribute "+type+" a"+suffix+
                ";attribute vec2 p;varying float color;float seed="+expression+
                ";void main(){gl_Position=vec4(p,0,1);color=seed;}";
            const auto artifact=vispy::shader::build_portable_shader(source,
                "varying float color;void main(){gl_FragColor=vec4(color);}",{},"aggregate-binding-contract");
            check(artifact->ok,artifact->error);
            check(artifact->attributes.size()==layout.locations+1,"live physical reflection count");
            check(artifact->attributes.front().name=="a"+(shape.empty()?std::string(""):shape.size()==1?"[0]":"[0][0]")+"[0]" &&
                artifact->attributes.back().name=="p" && artifact->attributes.back().location==layout.locations,"dead input compaction");
        }
    for (const auto& type : {"float","int","uint","vec2","ivec3","uvec4"}) {
        NormAttribute logical{"a",type,0};logical.array_dimensions={2,3};AttributeLayout layout;std::string error;
        check(attribute_layout(logical,layout,error),error);
        const auto tail=attribute_location(layout,5);
        check(tail.name=="a[1][2]" && tail.binding_views.size()==3 &&
            tail.binding_views[1].word_offset==2*layout.value_type.rows,"vector array views");
    }
    for (const auto& invalid : {std::vector<uint32_t>{0}, {UINT32_MAX}, {65536,65536}}) {
        NormAttribute logical{"a","mat4",0};logical.array_dimensions=invalid;
        AttributeLayout unchanged;unchanged.name="sentinel";std::string error;
        check(!attribute_layout(logical,unchanged,error) && unchanged.name=="sentinel","shape rejection is atomic");
    }
}
