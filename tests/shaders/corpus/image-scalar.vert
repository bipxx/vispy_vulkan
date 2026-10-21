vec4 null_transform_map(vec4 pos) {return pos;}

vec4 transform_map_chain(vec4 pos) {
    vec4 result_1 = null_transform_map(pos);
    return result_1;
}

vec4 null_transform_map_1(vec4 pos) {return pos;}

vec4 transform_map_chain_1(vec4 pos) {
    vec4 result_1 = null_transform_map_1(pos);
    return result_1;
}

vec4 null_transform_map_2(vec4 pos) {return pos;}

vec4 transform_map_chain_2(vec4 pos) {
    vec4 result_1 = null_transform_map_2(pos);
    return result_1;
}

uniform vec4 u_scale;
uniform vec4 u_translate;

vec4 st_transform_map(vec4 pos) {
    return vec4(pos.xyz * u_scale.xyz + u_translate.xyz * pos.w, pos.w);
}


uniform vec4 u_scale_1;
uniform vec4 u_translate_1;

vec4 st_transform_map_1(vec4 pos) {
    return vec4(pos.xyz * u_scale_1.xyz + u_translate_1.xyz * pos.w, pos.w);
}


vec4 transform_map_chain_3(vec4 pos) {
    vec4 result_1 = st_transform_map(pos);
    vec4 result_2 = st_transform_map_1(result_1);
    return result_2;
}

uniform vec4 u_scale_2;
uniform vec4 u_translate_2;

vec4 st_transform_map_2(vec4 pos) {
    return vec4(pos.xyz * u_scale_2.xyz + u_translate_2.xyz * pos.w, pos.w);
}


vec4 transform_map_chain_4(vec4 pos) {
    vec4 result_1 = st_transform_map_2(pos);
    return result_1;
}

vec4 transform_map_chain_5(vec4 pos) {
    vec4 result_1 = transform_map_chain(pos);
    vec4 result_2 = transform_map_chain_1(result_1);
    vec4 result_3 = transform_map_chain_2(result_2);
    vec4 result_4 = transform_map_chain_3(result_3);
    vec4 result_5 = transform_map_chain_4(result_4);
    return result_5;
}


uniform int method;  // 0=subdivide, 1=impostor
attribute vec2 a_position;
attribute vec2 a_texcoord;
varying vec2 v_texcoord;

void main() {
    v_texcoord = a_texcoord;
    gl_Position = transform_map_chain_5(vec4(a_position, 0., 1.));
}

