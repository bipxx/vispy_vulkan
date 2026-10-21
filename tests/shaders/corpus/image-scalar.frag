uniform sampler2D u_texture_1;

vec4 texture_lookup(vec2 texcoord) {
    if(texcoord.x < 0.0 || texcoord.x > 1.0 ||
    texcoord.y < 0.0 || texcoord.y > 1.0) {
        discard;
    }
    return texture2D(u_texture_1, texcoord);
}

float color_to_luminance(vec4 color) { return color.r; }

uniform vec2 u_clim;

float apply_clim(float data) {
    // pass through NaN values to get handled by the colormap
    if (!(data <= 0.0 || 0.0 <= data)) return data;

    data = clamp(data, min(u_clim.x, u_clim.y), max(u_clim.x, u_clim.y));
    data = (data - u_clim.x) / (u_clim.y - u_clim.x);
    return data;
}

uniform float u_gamma;

float apply_gamma(float data) {
    // pass through NaN values to get handled by the colormap
    if (!(data <= 0.0 || 0.0 <= data)) return data;

    return pow(data, u_gamma);
}


vec4 grays(float t) {
    // Map NaN to bad_color
    if (!(t <= 0.0 || 0.0 <= t)) {
        return vec4(0.000, 0.000, 0.000, 0.000);
    }
    return vec4(t, t, t, 1.0);
}


vec4 chain(vec4 color) {
    float result_1 = color_to_luminance(color);
    float result_2 = apply_clim(result_1);
    float result_3 = apply_gamma(result_2);
    vec4 result_4 = grays(result_3);
    return result_4;
}

vec4 null_transform_map(vec4 pos) {return pos;}


uniform vec2 image_size;
uniform int method;  // 0=subdivide, 1=impostor
uniform sampler2D u_texture;
varying vec2 v_texcoord;

vec4 map_local_to_tex(vec4 x) {
    // Cast ray from 3D viewport to surface of image
    // (if null_transform_map does not affect z values, then this
    // can be optimized as simply null_transform_map.map(x) )
    vec4 p1 = null_transform_map(x);
    vec4 p2 = null_transform_map(x + vec4(0, 0, 0.5, 0));
    p1 /= p1.w;
    p2 /= p2.w;
    vec4 d = p2 - p1;
    float f = p2.z / d.z;
    vec4 p3 = p2 - d * f;

    // finally map local to texture coords
    return vec4(p3.xy / image_size, 0, 1);
}


void main()
{
    vec2 texcoord;
    if( method == 0 ) {
        texcoord = v_texcoord;
    }
    else {
        // vertex shader outputs clip coordinates;
        // fragment shader maps to texture coordinates
        texcoord = map_local_to_tex(vec4(v_texcoord, 0, 1)).xy;
    }

    gl_FragColor = chain(texture_lookup(texcoord));
}

