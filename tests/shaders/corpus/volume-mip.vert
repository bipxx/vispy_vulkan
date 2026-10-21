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

vec4 transform_map_chain_6(vec4 pos) {
    vec4 result_1 = transform_map_chain(pos);
    vec4 result_2 = transform_map_chain_1(result_1);
    return result_2;
}

vec4 null_transform_imap(vec4 pos) {return pos;}

vec4 transform_imap_chain(vec4 pos) {
    vec4 result_1 = null_transform_imap(pos);
    return result_1;
}

vec4 null_transform_imap_1(vec4 pos) {return pos;}

vec4 transform_imap_chain_1(vec4 pos) {
    vec4 result_1 = null_transform_imap_1(pos);
    return result_1;
}

vec4 transform_imap_chain_2(vec4 pos) {
    vec4 result_1 = transform_imap_chain(pos);
    vec4 result_2 = transform_imap_chain_1(result_1);
    return result_2;
}


attribute vec3 a_position;
uniform vec3 u_shape;

varying vec3 v_position;
varying vec4 v_nearpos;
varying vec4 v_farpos;

void main() {
    v_position = a_position;

    // Project local vertex coordinate to camera position. Then do a step
    // backward (in cam coords) and project back. Voila, we get our ray vector.
    vec4 pos_in_cam = transform_map_chain_6(vec4(v_position, 1));

    // intersection of ray and near clipping plane (z = -1 in clip coords)
    pos_in_cam.z = -pos_in_cam.w;
    v_nearpos = transform_imap_chain_2(pos_in_cam);

    // intersection of ray and far clipping plane (z = +1 in clip coords)
    pos_in_cam.z = pos_in_cam.w;
    v_farpos = transform_imap_chain_2(pos_in_cam);

    gl_Position = transform_map_chain_5(vec4(v_position, 1.0));
}

